"""Reads a Vista/7 .msstyles part table into parts.json, for the Aero tests' references.

usage: python3 tests/aero/msstyles.py EXTRACT_DIR LIBMSSTYLE_DIR

EXTRACT_DIR holds the resources wrestool dumped (`wrestool -x --raw -o EXTRACT_DIR/images aero.msstyles`): the class
map `aero.msstyles_CMAP_CMAP`, the property map `aero.msstyles_VARIANT_NORMAL` and one PNG per
`aero.msstyles_IMAGE_<id>`. Unlike XP's textual NORMALBLUE.ini, Vista and later keep the parts' properties as a binary
stream of 32-byte headers, each followed by its value. The format and the names of properties and parts are those of
libmsstyle (MIT, github.com/nptr/msstyleEditor); LIBMSSTYLE_DIR is its `libmsstyle` source folder, read for those
names only. Nothing from the theme is written into the repository.
"""

import json
import re
import struct
import sys
from pathlib import Path

HEADER = struct.Struct("<8i")
ENUM, STRING, INT, BOOL, COLOR, MARGINS, FILENAME, SIZE, POSITION, RECT, FONT, INTLIST = range(200, 212)
DISKSTREAM, STREAM = 213, 214
FLOAT_TYPES_END = 401
SHORT_TYPES = {FILENAME, 243, DISKSTREAM, FONT}
WORD_TYPES = {INT, SIZE, ENUM, 241}


def class_names(cmap):
    """The class map is a run of NUL-terminated UTF-16 names; empty ones do not count."""
    return [name for name in cmap.decode("utf-16-le").split("\0") if name]


def is_header(name, kind, class_id, part, state):
    if not (0 <= part <= 199 and 0 <= state <= 199 and 0 <= class_id <= 500):
        return False
    if not ENUM <= kind < FLOAT_TYPES_END:
        return False
    if name == kind and kind in (COLOR, FONT, DISKSTREAM, STREAM):
        return True
    return FLOAT_TYPES_END <= name <= 25000


def value_of(kind, short, size, data, cursor):
    """(value, bytes after the header) for one property."""
    if kind in SHORT_TYPES:
        return short, 0
    if short:
        return None, 0
    if kind in WORD_TYPES | {BOOL}:
        return struct.unpack_from("<i", data, cursor)[0], 8
    if kind == COLOR:
        colour = struct.unpack_from("<I", data, cursor)[0]
        return f"#{colour & 0xFF:02X}{colour >> 8 & 0xFF:02X}{colour >> 16 & 0xFF:02X}", 8
    if kind == POSITION:
        return list(struct.unpack_from("<2i", data, cursor)), 8
    if kind in (MARGINS, RECT):
        return list(struct.unpack_from("<4i", data, cursor)), 16
    if kind == STRING:
        return data[cursor : cursor + size - 2].decode("utf-16-le"), size
    if kind == INTLIST:
        count = struct.unpack_from("<i", data, cursor)[0] if size else 0
        return list(struct.unpack_from(f"<{count}i", data, cursor + 4)), 4 + 4 * count if size else 0
    return None, size


def properties(pmap):
    """Every (class id, part, state, name id, value) in the property stream, skipping padding between them."""
    cursor = 0
    while cursor < len(pmap) - HEADER.size:
        name, kind, class_id, part, state, short, _reserved, size = HEADER.unpack_from(pmap, cursor)
        if not is_header(name, kind, class_id, part, state):
            cursor += 1
            continue
        value, length = value_of(kind, short, size, pmap, cursor + HEADER.size)
        yield class_id, part, state, name, value
        cursor += HEADER.size + length


def property_names(libmsstyle):
    source = (libmsstyle / "VisualStyleDefinitions.cs").read_text(encoding="utf-8-sig")
    enum = source[source.index("enum IDENTIFIER") :]
    names = {}
    for name, number in re.findall(r"^\s*([A-Z_0-9]+)\s*=\s*(\d+)", enum[: enum.index("}")], re.M):
        names.setdefault(int(number), name)
    return names


def part_names(libmsstyle):
    """{"WINDOW": {1: "CAPTION", ...}} from the PARTS_<CLASS> lists."""
    source = (libmsstyle / "VisualStylePartMap.cs").read_text(encoding="utf-8-sig")
    tables = {}
    for table, body in re.findall(
        r"PARTS_([A-Z_0-9]+)\s*=\s*new List<VisualStylePartEntry>\(\)\s*\{(.*?)\};", source, re.S
    ):
        tables[table] = {int(number): name for number, name in re.findall(r"Entry\((\d+), \"([^\"]+)\"", body)}
    return tables


def parts_of(class_name, parts):
    """DWM's glass frame parts are numbered differently in each Windows release; this table is Windows 7's."""
    key = class_name.split("::")[-1].upper()
    return parts.get("DWMWINDOW_WIN7" if key == "DWMWINDOW" else key, {})


def part_table(extract, libmsstyle):
    """{class: {part: {state: {property: value}}}}, image files named as the extracted PNGs."""
    images = extract / "images"
    classes = class_names((images / "aero.msstyles_CMAP_CMAP").read_bytes())
    names, parts = property_names(libmsstyle), part_names(libmsstyle)
    table = {}
    for class_id, part, state, name, value in properties((images / "aero.msstyles_VARIANT_NORMAL").read_bytes()):
        class_name = classes[class_id]
        part_name = parts_of(class_name, parts).get(part, str(part))
        property_name = names.get(name, str(name))
        is_image = property_name.startswith("IMAGEFILE") or property_name.endswith("IMAGEFILE")
        stored = (
            f"images/aero.msstyles_IMAGE_{value}"
            if is_image
            else f"images/aero.msstyles_STREAM_{value}"
            if property_name == "DISKSTREAM"
            else value
        )
        table.setdefault(class_name, {}).setdefault(part_name, {}).setdefault(str(state), {})[property_name] = stored
    return table


if __name__ == "__main__":
    extract, libmsstyle = Path(sys.argv[1]), Path(sys.argv[2])
    (extract / "parts.json").write_text(json.dumps(part_table(extract, libmsstyle), indent=1, sort_keys=True))
    print("wrote", extract / "parts.json")
