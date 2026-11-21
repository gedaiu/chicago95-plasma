"""Local recent documents recorded by GTK and KDE, newest first."""

import configparser
import json
import os
import sys
from datetime import UTC, datetime
from itertools import chain
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree


def timestamp(value):
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return (stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)).timestamp()
    except (ValueError, OverflowError):
        return 0


def xbel_documents(history, names):
    try:
        bookmarks = ElementTree.parse(history).getroot().findall("bookmark")
    except (OSError, ElementTree.ParseError):
        return
    for bookmark in bookmarks:
        if names is None:
            yield bookmark.get("href", ""), timestamp(bookmark.get("modified", ""))
            continue
        for record in bookmark.findall(".//{*}application"):
            if record.get("name", "").casefold().removesuffix(".desktop") not in names:
                continue
            date = record.get("modified") or bookmark.get("modified", "")
            yield bookmark.get("href", ""), timestamp(date)


def kde_documents(folder, names):
    for link in folder.glob("*.desktop"):
        entry = configparser.ConfigParser(interpolation=None, strict=False)
        try:
            entry.read(link, encoding="utf-8")
            group = entry["Desktop Entry"]
            owner = group.get("X-KDE-LastOpenedWith", "")
            if names is not None and owner.casefold().removesuffix(".desktop") not in names:
                continue
            uri = group.get("URL") or os.path.expandvars(group.get("URL[$e]", ""))
            yield uri, link.stat().st_mtime
        except (KeyError, configparser.Error, UnicodeError, OSError):
            continue


def recent_documents(limit=12, *, names=None, query=""):
    if limit <= 0:
        return []
    folder = Path(os.getenv("XDG_DATA_HOME") or Path.home() / ".local/share")
    bookmarks = xbel_documents(folder / "recently-used.xbel", names)
    recents = {}
    query = query.casefold()
    for uri, when in chain(bookmarks, kde_documents(folder / "RecentDocuments", names)):
        try:
            url = urlsplit(uri)
        except ValueError:
            continue
        if url.scheme != "file" or url.netloc.casefold() not in ("", "localhost"):
            continue
        path = unquote(url.path)
        if path.startswith("/") and "\x00" not in path and query in Path(path).name.casefold():
            recents[path] = max(recents.get(path, when), when)
    documents = []
    for path in sorted(recents, key=recents.get, reverse=True):
        if os.path.exists(path):
            documents.append(path)
            if len(documents) == limit:
                break
    return documents


if __name__ == "__main__":
    print(json.dumps(recent_documents(30, query=sys.argv[1])))
