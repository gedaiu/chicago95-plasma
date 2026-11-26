"""Open a visual tolerance editor from parity capture directories, newest last."""

import argparse
import base64
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from urllib.parse import urlsplit

from PIL import Image
from report import RETIRED_CASES

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from visual_tolerances import DEFAULT_POLICY, approval_image  # noqa: E402

EMPTY_POLICY = {"version": 1, "cases": {}}


def collect(directories, reviewed=(), initial=None):
    cases = {key: capture for key, capture in (initial or {}).items() if key not in RETIRED_CASES}
    for directory in directories:
        visual = directory / "visual"
        for metrics in sorted(visual.rglob("comparison.metrics.json")):
            key = metrics.parent.relative_to(visual).as_posix()
            if key in RETIRED_CASES:
                continue
            try:
                data = json.loads(metrics.read_text())
            except FileNotFoundError:
                continue  # pytest may be resetting the capture directory
            size = data["reference_size"]
            if size != data["rendered_size"]:
                cases.pop(key, None)
                continue
            if data["changed_pixels"]:
                try:
                    panel = metrics.with_name("comparison.png").read_bytes()
                except FileNotFoundError:
                    continue
            elif key in reviewed and data["compared_pixels"] == size[0] * size[1]:
                # Keep the review available once all pixels match. The strict
                # test only writes a comparison panel when it finds differences.
                try:
                    with Image.open(metrics.with_name("rendered.png")) as rendered:
                        match = Image.new("RGB", (size[0] * 3, size[1]))
                        match.paste(rendered, (0, 0))
                        match.paste(rendered, (size[0], 0))
                except FileNotFoundError:
                    continue
                stream = BytesIO()
                match.save(stream, format="PNG")
                panel = stream.getvalue()
            else:
                cases.pop(key, None)
                continue
            cases[key] = {
                "size": size,
                "changed": data["changed_pixels"],
                "passed": data.get("pixels_over_tolerance", data["changed_pixels"]) == 0,
                "png": base64.b64encode(panel).decode("ascii"),
            }
    return cases


def load_policy(path):
    if not path.exists():
        return {"version": 1, "cases": {}}
    policy = json.loads(path.read_text())
    if not isinstance(policy, dict) or policy.get("version") != 1 or not isinstance(policy.get("cases"), dict):
        raise ValueError(f"{path}: expected a version 1 tolerance policy")
    return policy


def valid_box(mark, size):
    fields = ("x", "y", "width", "height")
    if not isinstance(mark, dict) or any(type(mark.get(field)) is not int for field in fields):
        return False
    x, y, w, h = (mark[field] for field in fields)
    width, height = size
    return 0 <= x < x + w <= width and 0 <= y < y + h <= height


def valid_entry(entry, size):
    if not isinstance(entry, dict) or entry.get("size") != size or not isinstance(entry.get("regions"), list):
        return False
    if "review" in entry:
        review = entry["review"]
        if (
            not isinstance(review, dict)
            or review.get("status") not in ("pending", "approved", "rejected")
            or not isinstance(review.get("comment"), str)
            or len(review["comment"]) > 10_000
        ):
            return False
    for rule in entry["regions"]:
        if not valid_box(rule, size) or type(rule.get("max_channel_delta")) is not int or not 0 <= rule["max_channel_delta"] <= 255:
            return False
    if "approved_pixels" in entry:
        if entry.get("review", {}).get("status") != "approved" or not isinstance(entry["approved_pixels"], str):
            return False
        try:
            approval_image(entry["approved_pixels"], size)
        except ValueError:
            return False
    annotations = entry.get("annotations", [])
    if not isinstance(annotations, list) or any(
        not valid_box(note, size) or not isinstance(note.get("text"), str)
        or len(note["text"]) > 10_000 or not note["text"].strip()
        for note in annotations
    ):
        return False
    return True


def write_policy(path, policy):
    with NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as temporary:
        staging = Path(temporary.name)
        try:
            json.dump(policy, temporary, indent=2)
            temporary.write("\n")
            temporary.close()
            staging.replace(path)
        finally:
            staging.unlink(missing_ok=True)


def render_page(captures, *, server):
    template = Path(__file__).with_suffix(".html").read_text()
    page = template.replace("/* CAPTURES */", json.dumps(captures).replace("<", "\\u003c"))
    return page.replace("/* SERVER */", json.dumps(server))


def serve(captures, policy_path, port, *, directories=()):
    origin = f"http://127.0.0.1:{port}"
    if not policy_path.exists():
        write_policy(policy_path, EMPTY_POLICY)
    load_policy(policy_path)
    writes = Lock()
    initial = captures = collect((), initial=captures)
    page = render_page(captures, server=True).encode()

    class EditorHandler(BaseHTTPRequestHandler):
        def respond(self, status, content_type, content):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

        def json_response(self, status, value):
            self.respond(status, "application/json; charset=utf-8", json.dumps(value).encode())

        def do_GET(self):
            nonlocal captures
            if self.headers.get("Host") != f"127.0.0.1:{port}":
                self.send_error(403)
            elif urlsplit(self.path).path == "/":
                if directories:
                    reviewed = load_policy(policy_path)["cases"]
                    latest = collect(directories, reviewed, initial=initial)
                    captures = latest
                    self.respond(200, "text/html; charset=utf-8", render_page(latest, server=True).encode())
                else:
                    self.respond(200, "text/html; charset=utf-8", page)
            elif self.path == "/api/policy":
                try:
                    policy = load_policy(policy_path)
                except (OSError, ValueError) as error:
                    self.json_response(500, {"error": str(error)})
                else:
                    self.json_response(200, policy)
            else:
                self.send_error(404)

        def do_PUT(self):
            if self.path != "/api/policy":
                self.send_error(404)
                return
            if self.headers.get("Origin") != origin or self.headers.get_content_type() != "application/json":
                self.send_error(403)
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 8_000_000:
                    raise ValueError("Invalid policy request size")
                request = json.loads(self.rfile.read(length))
                key, entry, previous = (request[field] for field in ("case", "entry", "previous"))
                if key not in captures or (entry is not None and not valid_entry(entry, captures[key]["size"])):
                    raise ValueError("Invalid capture, painted pixels, or review")
            except (ValueError, KeyError, TypeError) as error:
                self.json_response(400, {"error": str(error)})
                return
            try:
                with writes:
                    policy = load_policy(policy_path)
                    saved = policy["cases"].get(key)
                    if saved != previous and saved != entry:
                        self.json_response(409, {"error": "This capture changed in another tab. Reload to see the saved edits."})
                        return
                    if saved != entry:
                        if entry is None:
                            del policy["cases"][key]
                        else:
                            policy["cases"][key] = entry
                        write_policy(policy_path, policy)
            except (OSError, ValueError) as error:
                self.json_response(500, {"error": str(error)})
            else:
                self.json_response(200, {"saved": True})

    with ThreadingHTTPServer(("127.0.0.1", port), EditorHandler) as server:
        print(f"{origin}/ · {len(captures)} captures · saves to {policy_path}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="+", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, help="build a standalone HTML file")
    mode.add_argument("--serve", action="store_true", help="start the localhost editor with autosave")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY, help="JSON file saved by the local server")
    args = parser.parse_args()
    cases = collect(args.directories, load_policy(args.policy)["cases"])
    if not cases:
        parser.error("no same-size mismatches or reviewed matches found")
    if args.serve:
        serve(cases, args.policy.resolve(), args.port, directories=args.directories)
    else:
        args.output.write_text(render_page(cases, server=False))
        print(f"{args.output} · {len(cases)} captures")


if __name__ == "__main__":
    main()
