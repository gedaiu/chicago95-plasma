"""Compare a Blender calibration render with the original atlas and record the rig tests."""

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SIZE = (124, 93)


def composite(image, size=SIZE, background="white"):
    canvas = Image.new("RGBA", size, background)
    canvas.alpha_composite(image.resize(size, Image.Resampling.LANCZOS))
    return canvas.convert("RGB")


def paper_median(image):
    array = np.asarray(image.resize(SIZE, Image.Resampling.LANCZOS)).astype(float)
    red, green, blue, alpha = array.transpose(2, 0, 1)
    yellow = (alpha > 200) & (red > blue + 20) & (green > blue + 20) & (abs(red - green) < 20)
    return np.median(array[:, :, :3][yellow], axis=0).tolist()


def original_frames(name):
    text = (ROOT / "data/clippy/agent.js").read_text()
    data = json.loads(text[text.index("{") : text.rindex("}") + 1])
    atlas = Image.open(ROOT / "data/clippy/map.png").convert("RGBA")
    frames = []
    for frame in data["animations"][name]["frames"]:
        image = Image.new("RGBA", SIZE)
        for x, y in frame.get("images", []):
            image.alpha_composite(atlas.crop((x, y, x + 124, y + 93)))
        frames.append((image, frame.get("duration", 100)))
    return frames


def at_time(frames, milliseconds):
    for image, duration in frames:
        milliseconds -= duration
        if milliseconds < 0:
            return image
    return frames[-1][0]


def review(folder):
    manifest = json.loads((folder / "manifest.json").read_text())
    reference = original_frames("RestPose")[0][0]
    images = {name: Image.open(folder / f"{name}.png").convert("RGBA") for name in ("baseline", "rest")}
    target = np.asarray(composite(reference)).astype(float)
    metrics = {}
    target_alpha = np.asarray(reference.getchannel("A")) >= 128
    for name, image in images.items():
        pixels = np.asarray(composite(image)).astype(float)
        alpha = np.asarray(image.resize(SIZE, Image.Resampling.LANCZOS).getchannel("A")) >= 128
        metrics[name] = {
            "mean_rgb_error_0_255": float(np.abs(pixels - target).mean()),
            "silhouette_iou": float(np.count_nonzero(alpha & target_alpha) / np.count_nonzero(alpha | target_alpha)),
            "paper_rgb_median": paper_median(image),
        }
    report = {
        "original_paper_rgb_median": paper_median(reference),
        "renders": metrics,
        "note": "Color statistics are heuristic yellow-paper samples. Geometry/animation fidelity is NOT certified.",
    }
    if len(manifest["sequences"]) > 1:
        returned = np.asarray(Image.open(folder / "rest-return.png").convert("RGBA"))
        assert np.array_equal(returned, np.asarray(images["rest"])), "Rig did not return exactly to its rest render"
        report["rest_return_pixel_identical"] = True
    for items in manifest["sequences"].values():
        for item in items:
            image = Image.open(folder / item["file"])
            assert image.size == tuple(manifest["pixel_size"]) and image.mode == "RGBA"
            assert image.getchannel("A").getextrema() == (0, 255)
    (folder / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    contact = Image.new("RGB", (3 * 496, 550), "#008080")
    draw = ImageDraw.Draw(contact)
    for column, (label, image) in enumerate(
        (("Original", reference), ("Baseline", images["baseline"]), ("Calibrated prototype", images["rest"]))
    ):
        draw.text((column * 496 + 12, 10), label, fill="white", font=font)
        # Show the actual HD result above; original is nearest-neighbour enlarged.
        enlarged = image.resize((496, 372), Image.Resampling.NEAREST if column == 0 else Image.Resampling.LANCZOS)
        contact.paste(enlarged, (column * 496, 40), enlarged)
        native = image.resize(SIZE, Image.Resampling.LANCZOS)
        contact.paste(native, (column * 496 + 186, 440), native)
    contact.save(folder / "materials-comparison.png")
    if len(manifest["sequences"]) == 1:
        return report
    command = [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        "1024x560",
        "-framerate",
        "50",
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(folder / "prototype-comparison.mp4"),
    ]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as process:
        for name, items in manifest["sequences"].items():
            frames = [(Image.open(folder / item["file"]).convert("RGBA"), item["duration_ms"]) for item in items]
            refs = original_frames("Idle1_1" if name == "Blink" else name)
            if name == "Blink":
                refs = refs[:5]  # First original blink, not the entire idle loop.
            total = sum(duration for _, duration in frames)
            ref_total = sum(duration for _, duration in refs)
            for time in range(0, total, 20):
                canvas = Image.new("RGB", (1024, 560), "#008080")
                draw = ImageDraw.Draw(canvas)
                draw.text((12, 10), f"Original: {name}", fill="white", font=font)
                draw.text((524, 10), "3D prototype — durations normalized", fill="white", font=font)
                for column, image in enumerate((at_time(refs, time / total * ref_total), at_time(frames, time))):
                    large = image.resize(
                        (496, 372), Image.Resampling.NEAREST if column == 0 else Image.Resampling.LANCZOS
                    )
                    canvas.paste(large, (column * 512 + 8, 45), large)
                    native = image.resize(SIZE, Image.Resampling.LANCZOS)
                    canvas.paste(native, (column * 512 + 194, 440), native)
                process.stdin.write(canvas.tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise RuntimeError("Video encoding failed")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    print(json.dumps(review(parser.parse_args().folder), indent=2))
