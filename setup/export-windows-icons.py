#!/usr/bin/env python3
"""Export PNG icon frames from the Windows and Program Files folders of a mounted VM."""

import argparse
import csv
import json
import os
import re
import struct
import subprocess
from collections import Counter
from itertools import groupby
from pathlib import Path
from urllib.parse import quote

import pefile
from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage, QImageReader

INSTALL_FOLDERS = {"windows", "winnt", "program files", "program files (x86)"}
ICON_DIRECTORY = struct.Struct("<3H")
ICON_FRAME = struct.Struct("<4B2H2I")
GROUP_FRAME = struct.Struct("<4B2HIH")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def executable_format(path):
    with path.open("rb") as file:
        header = file.read(64)
        if len(header) == 64 and header.startswith(b"MZ"):
            file.seek(struct.unpack_from("<I", header, 60)[0])
            return file.read(4)
        if path.suffix.casefold() == ".ico" and header.startswith(b"\0\0\1\0"):
            return b"ICO"
    return None


def read_icon_frames(data):
    reserved, kind, count = ICON_DIRECTORY.unpack_from(data)
    if reserved or kind != 1 or not count:
        raise ValueError("invalid icon directory")
    for index in range(count):
        fields = ICON_FRAME.unpack_from(data, ICON_DIRECTORY.size + index * ICON_FRAME.size)
        length, offset = fields[-2:]
        if offset + length > len(data):
            raise ValueError(f"truncated ICO frame {index + 1}")
        yield fields[:6], data[offset : offset + length]


def decode_dib(image, fields):
    offset = ICON_DIRECTORY.size + ICON_FRAME.size
    ico = ICON_DIRECTORY.pack(0, 1, 1) + ICON_FRAME.pack(*fields, len(image), offset) + image
    buffer = QBuffer()
    buffer.setData(ico)
    buffer.open(QIODevice.ReadOnly)
    return QImageReader(buffer, b"ico").read()


def read_icon_resource(image, fields):
    if image.startswith(PNG_SIGNATURE):
        decoded = QImage.fromData(image)
    else:
        decoded = decode_dib(image, fields)
        if decoded.isNull():
            # Some legacy groups declare the doubled height of the XOR and AND masks.
            width, height, planes, depth = dib_dimensions(image)
            if width <= 256 and height <= 256:
                decoded = decode_dib(image, (width % 256, height % 256, 0, 0, planes, depth))
            elif depth == 32:
                decoded = oversized_icon(image, width, height)
    if decoded.isNull():
        raise ValueError("invalid icon image")
    return decoded.convertToFormat(QImage.Format_RGBA8888)


def resource_id(entry):
    return int(entry.id) if entry.name is None else str(entry.name)


def pe_resources(path):
    with pefile.PE(str(path), fast_load=True) as module:
        module.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
        resources = getattr(module, "DIRECTORY_ENTRY_RESOURCE", None)
        if resources is None:
            return {}
        return {
            kind.id: {
                (resource_id(entry), resource_id(language)): module.get_data(
                    language.data.struct.OffsetToData, language.data.struct.Size
                )
                for entry in kind.directory.entries
                for language in entry.directory.entries
            }
            for kind in resources.entries
            if kind.id in (3, 14)
        }


def icon_groups(resources, issue):
    frames = resources.get(3, {})
    groups = resources.get(14, {})
    used = set()
    languages = {}
    for frame_id, lang in frames:
        languages.setdefault(frame_id, []).append(lang)
    for (group_id, lang), group in groups.items():
        try:
            reserved, kind, count = ICON_DIRECTORY.unpack_from(group)
            if reserved or kind != 1:
                raise ValueError("invalid icon group")
            for index in range(count):
                fields = GROUP_FRAME.unpack_from(group, ICON_DIRECTORY.size + index * GROUP_FRAME.size)
                frame_id = fields[-1]
                choices = languages.get(frame_id, [])
                if not choices:
                    issue(group_id, lang, f"missing RT_ICON {frame_id}")
                    continue
                frame_language = lang if lang in choices else 0 if 0 in choices else choices[0]
                key = frame_id, frame_language
                used.add(key)
                yield resource_label("group", group_id), lang, index + 1, frame_id, fields[:6], frames[key]
        except (ValueError, struct.error) as error:
            issue(group_id, lang, str(error))
    for (frame_id, lang), payload in frames.items():
        if (frame_id, lang) in used:
            continue
        try:
            fields = standalone_fields(payload)
            yield resource_label("resource", frame_id), lang, 1, frame_id, fields, payload
        except (ValueError, struct.error) as error:
            issue(frame_id, lang, str(error))


def standalone_fields(payload):
    if payload.startswith(PNG_SIGNATURE):
        return (0, 0, 0, 0, 1, 32)
    width, height, planes, depth = dib_dimensions(payload)
    return width % 256, height % 256, 0, 0, planes, depth


def dib_dimensions(payload):
    header_size = struct.unpack_from("<I", payload)[0]
    if header_size == 12:
        width, height, planes, depth = struct.unpack_from("<4H", payload, 4)
    elif header_size >= 40:
        width, height, planes, depth = struct.unpack_from("<2i2H", payload, 4)
    else:
        raise ValueError("unsupported icon bitmap header")
    height = abs(height) // 2
    if not (1 <= width and 1 <= height):
        raise ValueError(f"invalid icon dimensions {width}x{height}")
    return width, height, planes, depth


def oversized_icon(payload, width, height):
    header_size = struct.unpack_from("<I", payload)[0]
    if header_size != 40 or struct.unpack_from("<I", payload, 16)[0]:
        raise ValueError("unsupported oversized icon format")
    end = header_size + width * height * 4
    image = Image.frombytes("RGBA", (width, height), payload[header_size:end], "raw", "BGRA", 0, -1)
    if image.getchannel("A").getbbox() is None:
        stride = ((width + 31) // 32) * 4
        alpha = Image.frombytes("1", image.size, payload[end:], "raw", "1;I", stride, -1)
        image.putalpha(alpha.convert("L"))
    return QImage(image.tobytes(), width, height, QImage.Format_RGBA8888).copy()


def resource_label(kind, identifier):
    return f"{kind}-{identifier}" if isinstance(identifier, int) else f"{kind}-name-{identifier}"


def ne_resources(path):
    listing = subprocess.run(["wrestool", "-l", path], capture_output=True, check=True, text=True, errors="replace")
    entries = re.finditer(
        r"--type=(3|14) --name=(?:'([^']+)'|(\d+)) \[\S+ offset=(0x[0-9a-f]+) size=(\d+)\]",
        listing.stdout,
    )
    resources = {3: {}, 14: {}}
    with path.open("rb") as file:
        for entry in entries:
            kind, named, numeric, offset, size = entry.groups()
            file.seek(int(offset, 16))
            resources[int(kind)][(named if named is not None else int(numeric), "")] = file.read(int(size))
    return resources


def source_frames(source, signature, issue):
    if signature == b"PE\0\0":
        yield from icon_groups(pe_resources(source), issue)
    elif signature.startswith(b"NE"):
        yield from icon_groups(ne_resources(source), issue)
    elif signature == b"ICO":
        for index, (fields, image) in enumerate(read_icon_frames(source.read_bytes()), start=1):
            yield "file", "", index, "", fields, image


def decoded_frames(source, signature, issue):
    for group, lang, frame, resource, fields, image in source_frames(source, signature, issue):
        try:
            yield group, lang, frame, resource, fields[5], read_icon_resource(image, fields)
        except (ValueError, struct.error) as error:
            issue(group, lang, str(error))


def largest_frames(frames):
    for _, variants in groupby(frames, key=lambda frame: frame[:2]):
        yield max(variants, key=lambda frame: (frame[5].width() * frame[5].height(), frame[4]))


def export_icons(root, folders, output, *, all_sizes=False):
    counts = Counter(files=0, source_files=0, groups=0, frames=0, issues=0)
    with (
        (output / "index.tsv").open("w", encoding="utf-8", newline="") as catalog,
        (output / "issues.tsv").open("w", encoding="utf-8", newline="") as failures,
    ):
        index = csv.writer(catalog, delimiter="\t")
        errors = csv.writer(failures, delimiter="\t")
        index.writerow(("source", "group", "language", "frame", "resource", "width", "height", "bit_depth", "png"))
        errors.writerow(("source", "resource", "language", "issue"))
        for folder in folders:
            for directory, subdirectories, filenames in os.walk(folder):
                subdirectories.sort()
                for filename in sorted(filenames):
                    source = Path(directory) / filename
                    if source.is_symlink() or not source.is_file():
                        continue
                    counts["files"] += 1
                    relative = source.relative_to(root)
                    source_name = relative.as_posix()
                    groups = set()

                    def issue(group, lang, message, source_name=source_name):
                        errors.writerow((source_name, group, lang, message.partition("\n")[0]))
                        counts["issues"] += 1

                    try:
                        signature = executable_format(source)
                        if signature is None:
                            continue
                        frames = decoded_frames(source, signature, issue)
                        if not all_sizes:
                            frames = largest_frames(frames)
                        for group, lang, frame, resource, depth, decoded in frames:
                            try:
                                width, height = decoded.width(), decoded.height()
                                name = f"{frame:02d}-{width}x{height}-{depth}bpp.png"
                                group_dir = quote(f"{group}-lang-{lang}" if lang != "" else group, safe="")
                                target = Path("png") / relative / group_dir / name
                                file = output / target
                                file.parent.mkdir(parents=True, exist_ok=True)
                                if not decoded.save(str(file)):
                                    raise OSError(f"could not write {target}")
                                index.writerow(
                                    (
                                        relative.as_posix(),
                                        group,
                                        lang,
                                        frame,
                                        resource,
                                        width,
                                        height,
                                        depth,
                                        target.as_posix(),
                                    )
                                )
                                groups.add((group, lang))
                                counts["frames"] += 1
                            except OSError as error:
                                issue(group, lang, str(error))
                    except (
                        OSError,
                        ValueError,
                        struct.error,
                        pefile.PEFormatError,
                        subprocess.CalledProcessError,
                    ) as error:
                        issue("", "", str(error))
                    if groups:
                        counts["source_files"] += 1
                        counts["groups"] += len(groups)
    return {"folders": [folder.relative_to(root).as_posix() for folder in folders], "all_sizes": all_sizes, **counts}


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, epilog="Requires Python pefile, Pillow, PySide6, and wrestool from icoutils."
    )
    parser.add_argument("windows_root", type=Path, help="mounted Windows disk")
    parser.add_argument("output", type=Path, help="new directory for the catalog and PNGs")
    parser.add_argument("--all-sizes", action="store_true", help="keep every frame instead of the largest per group")
    args = parser.parse_args()
    try:
        root = args.windows_root.resolve(strict=True)
        folders = sorted(p for p in root.iterdir() if p.name.casefold() in INSTALL_FOLDERS and p.is_dir())
        if not folders:
            raise ValueError("no Windows, WINNT, or Program Files folders found")
        args.output.mkdir(parents=True)
        summary = export_icons(root, folders, args.output, all_sizes=args.all_sizes)
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
