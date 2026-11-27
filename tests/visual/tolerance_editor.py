"""Open a visual tolerance editor from parity capture directories, newest last."""

import argparse
import base64
import hashlib
import json
import os
import shutil
import sys
from fcntl import LOCK_EX, LOCK_SH, flock
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile, gettempdir
from threading import Lock
from urllib.parse import parse_qs, urlsplit

import numpy as np
from PIL import Image
from report import RETIRED_CASES

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from visual_tolerances import DEFAULT_POLICY, approval_image, tolerance_map  # noqa: E402

EMPTY_POLICY = {"version": 1, "cases": {}}
CHECKOUT = hashlib.sha256(os.fsencode(Path(__file__).resolve().parents[2])).hexdigest()[:12]
LATEST = Path(gettempdir()) / f"chicago95-visual-{os.getuid()}-{CHECKOUT}"
CAPTURE_FILES = (
    "rendered.png", "comparison.png", "comparison-reference.png", "comparison-rendered.png",
    "comparison.metrics.json",
)


def publish_run(run, latest=LATEST):
    """Keep the latest comparison for each case after pytest prunes its run directory."""
    if run.resolve() == latest.resolve():
        return
    latest.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (latest / ".lock").open("a") as lock:
        flock(lock, LOCK_EX)
        os.utime(lock.fileno())  # Invalidate the live index, including after a partial publication.
        for measured in sorted((run / "visual").rglob("comparison.metrics.json")):
            target = latest / measured.parent.relative_to(run)
            target.mkdir(parents=True, exist_ok=True)
            for name in CAPTURE_FILES:
                path = measured.with_name(name)
                if path.is_file():
                    with NamedTemporaryFile(dir=target, delete=False) as staging:
                        temporary = Path(staging.name)
                        try:
                            with path.open("rb") as source:
                                shutil.copyfileobj(source, staging)
                            staging.close()
                            temporary.replace(target / name)
                        finally:
                            temporary.unlink(missing_ok=True)
                else:
                    (target / name).unlink(missing_ok=True)


def panel_bytes(files):
    if "panel" in files:
        return files["panel"].read_bytes()
    # Older exact matches only saved the rendered image.
    with Image.open(files["match"]) as rendered:
        w, h = rendered.size
        match = Image.new("RGB", (w * 3, h))
        match.paste(rendered, (0, 0))
        match.paste(rendered, (w, 0))
    stream = BytesIO()
    match.save(stream, format="PNG")
    return stream.getvalue()


def collect(directories, *, embed=True):
    cases = {}
    for directory in directories:
        visual = directory / "visual"
        for metrics in sorted(visual.rglob("comparison.metrics.json")):
            key = metrics.parent.relative_to(visual).as_posix()
            if key in RETIRED_CASES:
                continue
            try:
                data = json.loads(metrics.read_text())
                revision = metrics.stat().st_mtime_ns
            except FileNotFoundError:
                continue  # pytest may be resetting the capture directory
            size = data["reference_size"]
            geometry = size != data["rendered_size"]
            panel = metrics.with_name("comparison.png")
            if geometry:
                files = {part: metrics.with_name(f"comparison-{part}.png") for part in ("reference", "rendered")}
            elif panel.is_file() or data["changed_pixels"]:
                files = {"panel": panel}
            else:
                files = {"match": metrics.with_name("rendered.png")}
            if not all(file.is_file() for file in files.values()):
                continue
            case = {
                "size": size,
                "changed": data["changed_pixels"],
                "passed": not geometry and data.get("pixels_over_tolerance", data["changed_pixels"]) == 0,
                "revision": str(revision),
            }
            if geometry:
                case["renderedSize"] = data["rendered_size"]
            if embed:
                try:
                    case["images"] = {
                        part: base64.b64encode(value).decode("ascii")
                        for part, value in (
                            ((part, path.read_bytes()) for part, path in files.items())
                            if geometry else (("panel", panel_bytes(files)),)
                        )
                    }
                except FileNotFoundError:
                    continue
            else:
                case["files"] = files
                case["metrics"] = metrics
            cases[key] = case
    return cases


def remaining_count(case, entry):
    """Apply the saved review to the pixels included in the test's difference panel."""
    size = tuple(case["size"])
    width, height = size
    with Image.open(case["files"]["panel"]) as image:
        if image.size != (3 * width, height):
            raise ValueError("Comparison dimensions changed")
        reference, rendered, difference = np.split(np.asarray(image.convert("RGB")), 3, axis=1)
    remaining = np.any(difference, axis=2)
    if entry["regions"]:
        delta = np.abs(reference.astype(np.int16) - rendered).max(axis=2)
        remaining &= delta > tolerance_map(size, entry["regions"])
    if entry.get("approved_pixels") and entry.get("review", {}).get("status") == "approved":
        approval = np.asarray(approval_image(entry["approved_pixels"], size))
        original, accepted = np.split(approval, 2, axis=1)
        if np.array_equal(reference, original):
            remaining &= np.any(rendered != accepted, axis=2)
    return int(remaining.sum())


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
        if not valid_box(rule, size):
            return False
        limit = rule.get("max_channel_delta")
        if type(limit) is not int or not 0 <= limit <= 255:
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


def serve(directories, policy_path, port):
    origin = f"http://127.0.0.1:{port}"
    if not policy_path.exists():
        write_policy(policy_path, EMPTY_POLICY)
    load_policy(policy_path)
    writes = Lock()
    LATEST.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock_path = LATEST / ".lock"
    published_only = not directories
    directories = (*directories, LATEST)
    cached_index = None
    captures = {}
    page = render_page({}, server=True).encode()

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
            nonlocal captures, cached_index
            url = urlsplit(self.path)
            if self.headers.get("Host") != f"127.0.0.1:{port}":
                self.send_error(403)
            elif url.path == "/":
                self.respond(200, "text/html; charset=utf-8", page)
            elif url.path == "/api/captures":
                with lock_path.open("a") as lock:
                    flock(lock, LOCK_SH)
                    generation = os.fstat(lock.fileno()).st_mtime_ns
                    if published_only and cached_index and cached_index[0] == generation:
                        _, revision, body = cached_index
                    else:
                        latest = collect(directories, embed=False)
                        payload = {
                            key: {k: v for k, v in case.items() if k not in ("files", "metrics")}
                            for key, case in latest.items()
                        }
                        revision = hashlib.sha256(json.dumps(payload).encode()).hexdigest()
                        body = json.dumps({"revision": revision, "captures": payload}).encode()
                        captures = latest
                        cached_index = generation, revision, body
                if parse_qs(url.query).get("since") == [revision]:
                    self.respond(204, "application/json", b"")
                else:
                    self.respond(200, "application/json; charset=utf-8", body)
            elif url.path == "/api/counts":
                # The sidebar can load before these comparisons are read. Only the
                # selected capture needs to send image data to the browser.
                current = captures
                result = {}
                try:
                    policy = load_policy(policy_path)
                    with lock_path.open("a") as lock:
                        flock(lock, LOCK_SH)
                        for key, entry in policy["cases"].items():
                            case = current.get(key)
                            if (not case or not case["changed"] or "renderedSize" in case
                                    or case["size"] != entry["size"]
                                    or not (entry["regions"] or entry.get("approved_pixels"))):
                                continue
                            try:
                                if str(case["metrics"].stat().st_mtime_ns) == case["revision"]:
                                    result[key] = [case["revision"], remaining_count(case, entry)]
                            except (FileNotFoundError, ValueError):
                                continue
                except (OSError, ValueError) as error:
                    self.json_response(500, {"error": str(error)})
                else:
                    self.json_response(200, result)
            elif url.path == "/api/image":
                args = parse_qs(url.query)
                key = args.get("case", [""])[0]
                part = args.get("part", ["panel"])[0]
                case = captures.get(key)
                if case is None or part not in (("reference", "rendered") if "renderedSize" in case else ("panel",)):
                    self.send_error(404)
                    return
                with lock_path.open("a") as lock:
                    flock(lock, LOCK_SH)
                    try:
                        revision = str(case["metrics"].stat().st_mtime_ns)
                        if args.get("revision") != [revision] or case["revision"] != revision:
                            self.send_error(409, "A newer capture is available")
                            return
                        files = case["files"]
                        image = panel_bytes(files) if part == "panel" else files[part].read_bytes()
                    except FileNotFoundError:
                        self.send_error(404)
                        return
                self.respond(200, "image/png", image)
            elif url.path == "/api/policy":
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
                case = captures.get(key)
                if case is None or "renderedSize" in case:
                    raise ValueError("Invalid capture")
                if entry is not None and not valid_entry(entry, case["size"]):
                    raise ValueError("Invalid capture, painted pixels, or review")
            except (ValueError, KeyError, TypeError) as error:
                self.json_response(400, {"error": str(error)})
                return
            try:
                with writes:
                    policy = load_policy(policy_path)
                    saved = policy["cases"].get(key)
                    if saved != previous and saved != entry:
                        self.json_response(
                            409, {"error": "This capture changed in another tab. Reload to see the saved edits."},
                        )
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
        print(f"{origin}/ · saves to {policy_path}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", nargs="*", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path, help="build a standalone HTML file")
    mode.add_argument("--serve", action="store_true", help="start the localhost editor with autosave")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY, help="JSON file saved by the local server")
    args = parser.parse_args()
    if args.serve:
        serve(args.directories, args.policy.resolve(), args.port)
    else:
        cases = collect((*args.directories, LATEST))
        if not cases:
            parser.error("no visual comparisons found")
        args.output.write_text(render_page(cases, server=False))
        print(f"{args.output} · {len(cases)} captures")


if __name__ == "__main__":
    main()
