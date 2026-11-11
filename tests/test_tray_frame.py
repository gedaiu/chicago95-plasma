"""The tray frame (plasmoids/org.chicago95.trayframe) over Plasma's system tray: what it takes away from Plasma's own
drawing. The pressed chevron opens Plasma's hidden-icons popup, and Plasma then lights the whole tray up with the
Plasma style's active tab behind the icons; the originals show nothing of the kind, and on Luna the tab's pale page
cut the blue tray box short."""

from conftest import REPO

TRAY_FRAME = REPO / "plasmoids/org.chicago95.trayframe/contents/ui/main.qml"


def test_the_tray_frame_hides_plasmas_tab_highlight_behind_the_tray_when_the_chevron_is_pressed():
    text = TRAY_FRAME.read_text()
    assert ('find(trayItem, 0, "CurrentItemHighLight")' in text, "highlight.visible = false" in text) == (True, True)
