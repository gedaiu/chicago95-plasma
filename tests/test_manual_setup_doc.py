"""The manual setup guide: linked from the README, and every repository path it names exists."""

import re

from conftest import REPO

GUIDE = REPO / "docs/manual-setup.md"
CODE_PATH = re.compile(r"`([\w.-]+/[^`\s*<>$]+)`")


def test_readme_links_the_manual_setup_guide():
    assert "(docs/manual-setup.md)" in (REPO / "README.md").read_text()


def test_every_repository_path_in_the_guide_exists():
    named = CODE_PATH.findall(GUIDE.read_text())
    in_repo = [path for path in named if not path.startswith("../") and (REPO / path.split("/")[0]).is_dir()]
    assert [path for path in in_repo if not (REPO / path.rstrip("/")).exists()] == []


def test_guide_shows_a_preview_for_each_part_of_the_basic_look():
    images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", GUIDE.read_text())
    assert (len(images) >= 4, [image for image in images if not (GUIDE.parent / image).is_file()]) == (True, [])
