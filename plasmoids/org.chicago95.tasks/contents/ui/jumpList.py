"""Windows 7 task menu entries supplied by the application and its recent documents."""

import json
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

# Setup copies this module beside the applet. In a checkout it lives in lib/.
if not Path(__file__).with_name("chicago95recent.py").is_file():
    sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "lib"))
from chicago95recent import recent_documents

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


def entries(app):
    actions = [{"label": app.get_action_name(key), "action": key} for key in app.list_actions()]
    names = {app.get_name().casefold(), app.get_id().casefold().removesuffix(".desktop")}
    executable = Path(app.get_executable()).name.casefold()
    if executable and executable not in ("env", "flatpak", "snap", "sh", "bash"):
        names.add(executable)
    documents = (Path(path) for path in recent_documents(10, names=names))
    return [{"label": path.name, "uri": path.as_uri()} for path in documents] + actions


def main(args):
    try:
        app = desktop_entry(args[0])
    except TypeError:  # GIO returns a null desktop entry for removed applications.
        app = None
    if len(args) == 1:
        print(json.dumps(entries(app) if app else []))
    elif app and args[1] == "action" and args[2] in app.list_actions():
        app.launch_action(args[2], None)
    elif app and args[1] == "uri":
        app.launch_uris([args[2]], None)


if __name__ == "__main__":
    main(sys.argv[1:])
