"""KRunner's results (data/qml/org/kde/milou, loaded ahead of Plasma's own through QML_IMPORT_PATH): the current
result is the selection, so it is drawn with the selected highlight (navy, like a drop-down's) and white text."""

from conftest import REPO
from test_quick_launch_drop import qml_block

MILOU = REPO / "data/qml/org/kde/milou"


def test_the_current_result_is_drawn_with_the_selected_highlight():
    highlight = qml_block((MILOU / "ResultsView.qml").read_text(), "highlight: PlasmaExtras.Highlight {")

    assert "pressed: true" in highlight


def test_the_current_results_text_is_the_highlighted_text_colour():
    delegate = (MILOU / "ResultDelegate.qml").read_text()

    assert (
        delegate.count(
            "(resultDelegate.down || resultDelegate.isCurrent) ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor"
        )
        == 3
    )


def test_the_override_module_shadows_plasmas_without_preferring_its_compiled_copy():
    qmldir = (MILOU / "qmldir").read_text()

    assert (
        "prefer " in qmldir,
        "ResultDelegate 254.0 ResultDelegate.qml" in qmldir,
        "ResultsView 254.0 ResultsView.qml" in qmldir,
    ) == (
        False,
        True,
        True,
    )
