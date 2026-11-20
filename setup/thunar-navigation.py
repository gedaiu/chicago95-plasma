"""Set Explorer navigation in an offline Thunar profile without resetting the other preferences."""

import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree

path = Path(sys.argv[1])
tree = ElementTree.parse(path)
for name, kind, value in (
    ("last-location-bar", "string", "ThunarLocationButtons"),
    ("last-menubar-visible", "bool", "false"),
):
    element = tree.find(f"property[@name='{name}']")
    if element is None:
        element = ElementTree.SubElement(tree.getroot(), "property", name=name)
    element.set("type", kind)
    element.set("value", value)
with NamedTemporaryFile(dir=path.parent, delete=False) as output:
    tree.write(output, encoding="utf-8", xml_declaration=True)
os.replace(output.name, path)
