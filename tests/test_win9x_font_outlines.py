from runpy import run_path

from conftest import REPO
from fontTools.pens.pointInsidePen import PointInsidePen

glyph_outline = run_path(str(REPO / "setup/import-win9x-fonts.py"))["glyph_outline"]


def test_stroke_outline_preserves_hole_diagonal_contact_and_bold_advance():
    # A ring and a detached dot that touches its corner. The strike stores
    # one column of eight bits for each scanline of this four-pixel-wide glyph.
    rows = ("1110", "1010", "1110", "0001")
    strike = bytearray(122)
    strike[95] = 65
    strike[118:122] = bytes((4, 0, 122, 0))
    strike.extend(int(row.ljust(8, "0"), 2) for row in rows)
    for bold in (False, True):
        glyph, metrics = glyph_outline(strike, 65, 4, 4, 64, bold)
        assert metrics == ((4 + bold) * 64, 0)
        # Regular has an outside contour, a counter, and a separate dot.
        if not bold:
            assert glyph.numberOfContours == 3
        for y, row in enumerate(rows):
            for x in range(5):
                expected = (x < 4 and row[x] == "1") or (bold and x > 0 and row[x - 1] == "1")
                pen = PointInsidePen(None, ((x + 0.5) * 64, (3.5 - y) * 64))
                glyph.draw(pen, None)
                assert pen.getResult() == expected


def test_blank_glyph_keeps_its_advance():
    strike = bytearray(123)
    strike[95] = 32
    strike[118:122] = bytes((4, 0, 122, 0))
    glyph, metrics = glyph_outline(strike, 32, 1, 1, 64, False)
    assert glyph.numberOfContours == 0
    assert metrics == (256, 0)
