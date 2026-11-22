"""Extract the Blue Luna comparison fixtures from a local XP installation CD."""

import argparse
import configparser
import io
import re
import struct
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops


def extract(iso, output):
    with tempfile.TemporaryDirectory() as scratch:
        cabinet = Path(scratch) / "luna.cab"
        with cabinet.open("wb") as stream:
            subprocess.run(["isoinfo", "-i", iso, "-x", "/I386/LUNA.MS_"], check=True, stdout=stream)
        style = Path(scratch) / "luna.msstyles"
        with style.open("wb") as stream:
            subprocess.run(["cabextract", "-p", cabinet], stdout=stream, check=True)

        def resource(kind, name):
            return subprocess.check_output(["wrestool", "-x", "-R", "-t", kind, "-n", name, style])

        settings = output / "settings"
        settings.mkdir(parents=True, exist_ok=True)
        ini = resource("TEXTFILE", "NORMALBLUE_INI").decode("utf-16le").rstrip("\0")
        (settings / "NORMALBLUE.ini").write_text(ini, encoding="utf-8")
        theme = configparser.ConfigParser(strict=False, interpolation=None, inline_comment_prefixes=(";",))
        theme.read_string(ini)
        keys = {}
        for section in theme.values():
            for prefix in ("", "glyph"):
                field = prefix + "imagefile"
                if field in section and section.get(prefix + "transparent", "").lower() == "true":
                    stem = section[field].split("\\")[-1].split(".")[0].upper()
                    colour = section.get(prefix + "transparentcolor", "255 0 255")
                    keys[f"BLUE_{stem}_BMP"] = tuple(map(int, colour.split()))
        images = output / "images"
        images.mkdir(exist_ok=True)
        listing = subprocess.check_output(["wrestool", "-l", "-t", "2", style], text=True)
        for name in re.findall(r"--name='(BLUE_[A-Z0-9_]+_BMP)'", listing):
            dib = resource("2", name)
            header, width, height, _, depth, compression = struct.unpack_from("<IiiHHI", dib)
            if depth == 32 and compression == 0:
                # Pillow normally discards the alpha byte in an uncompressed Windows DIB.
                image = Image.frombytes(
                    "RGBA", (width, abs(height)), dib[header:], "raw", "BGRA", 0, -1 if height > 0 else 1
                )
            else:
                image = Image.open(io.BytesIO(dib)).convert("RGB")
                if name in keys:
                    diff = ImageChops.difference(image, Image.new("RGB", image.size, keys[name]))
                    r, g, b = diff.split()
                    image.putalpha(ImageChops.lighter(ImageChops.lighter(r, g), b).point(lambda v: 255 if v else 0))
            image.save(images / f"{name}.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    extract(args.iso, args.output)
