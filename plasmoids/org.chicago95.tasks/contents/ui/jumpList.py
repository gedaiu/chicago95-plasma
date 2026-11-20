"""Windows 7 task menu entries supplied by the application and its recent documents."""

import json
import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse
from xml.etree import ElementTree

from gi.repository import Gio

try:
    from gi.repository.GioUnix import DesktopAppInfo
except ImportError:  # Older GLib exports the Unix desktop-entry API through Gio.
    from gi.repository.Gio import DesktopAppInfo


def desktop_entry(launcher):
    url = urlparse(launcher)
    if url.scheme == "file":
        return DesktopAppInfo.new_from_filename(unquote(url.path))
    name = unquote(url.path).lstrip("/")
    if url.scheme in ("", "applications") and name and "/" not in name:
        return DesktopAppInfo.new(name)
    return None


def entries(app, history):
    result = [{"label": app.get_action_name(key), "action": key} for key in app.list_actions()]
    try:
        bookmarks = ElementTree.parse(history).getroot().findall("bookmark")
    except (OSError, ElementTree.ParseError):
        return result
    names = {
        app.get_name().casefold(),
        app.get_id().removesuffix(".desktop").casefold(),
        Path(app.get_executable()).name.casefold(),
    }
    recent = sorted(bookmarks, key=lambda node: node.get("modified", ""), reverse=True)
    count = 0
    for bookmark in recent:
        if not any(node.get("name", "").casefold() in names for node in bookmark.findall(".//{*}application")):
            continue
        uri = bookmark.get("href", "")
        file = Gio.File.new_for_uri(uri)
        if file.is_native() and file.query_exists(None):
            result.append({"label": file.get_basename(), "uri": uri})
            count += 1
        if count == 10:
            break
    return result


def main(args):
    try:
        app = desktop_entry(args[0])
    except TypeError:  # GIO returns a null desktop entry for removed applications.
        app = None
    if len(args) == 1:
        history = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "recently-used.xbel"
        print(json.dumps(entries(app, history) if app else []))
    elif app and args[1] == "action" and args[2] in app.list_actions():
        app.launch_action(args[2], None)
    elif app and args[1] == "uri":
        app.launch_uris([args[2]], None)


if __name__ == "__main__":
    main(sys.argv[1:])
