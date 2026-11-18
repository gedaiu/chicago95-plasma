"""When Windows 7's superbar holds more buttons than fit, it pages them, with an up and down arrow at the band's end
(paging.js)."""

import pytest
from conftest import REPO
from js_library import call, load_js_library

BAND = {"room": 400, "buttonWidth": 60, "gap": 2, "arrowWidth": 17}


@pytest.fixture(scope="module")
def paging(qt_app):
    return load_js_library(REPO / "plasmoids/org.chicago95.tasks/contents/ui/paging.js")


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, {"perPage": 0, "pages": 1}),
        (6, {"perPage": 6, "pages": 1}),  # 6 buttons take 370 of 400
        (7, {"perPage": 6, "pages": 2}),  # 6 pitches of 62 and the arrows take 389 of 400
        (13, {"perPage": 6, "pages": 3}),
    ],
)
def test_window_count_gives_buttons_per_page_and_page_count(paging, count, expected):
    assert call(paging, "layout", count, BAND) == expected


def test_band_too_narrow_for_one_button_beside_the_arrows_still_pages_one_at_a_time(paging):
    assert call(paging, "layout", 3, {**BAND, "room": 50}) == {"perPage": 1, "pages": 3}


@pytest.mark.parametrize(("page", "pages", "expected"), [(0, 3, 0), (2, 3, 2), (3, 3, 2), (5, 2, 1), (-1, 2, 0)])
def test_page_is_kept_within_the_page_count(paging, page, pages, expected):
    assert call(paging, "clamped", page, pages) == expected
