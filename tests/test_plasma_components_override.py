"""Plasma's own icon buttons (KRunner's, the tray popups', the widgets') draw their icons grey until the pointer
is over them, as Explorer's toolbar did: data/qml/org/kde/plasma/components shadows Plasma's components module
through QML_IMPORT_PATH with one changed file, ButtonContent.qml; Setup links the rest of the module from the
system's copy (setup/steps.sh complete_qml_module)."""

import os

from conftest import REPO, run_bash_with_steps
from test_quick_launch_drop import qml_block

OURS = REPO / "data/qml/org/kde/plasma/components"


def test_our_button_content_greys_the_icon_unless_hovered_pressed_or_checked():
    icon = qml_block((OURS / "private/ButtonContent.qml").read_text(), "Kirigami.Icon {")

    assert (
        "layer.enabled: !(root.button.hovered || root.button.down || root.button.checked)" in icon,
        "saturation: -1.0" in icon,
        "import QtQuick.Effects" in (OURS / "private/ButtonContent.qml").read_text(),
    ) == (True, True, True)


def test_only_button_content_is_overridden_so_the_rest_of_the_module_is_plasmas():
    assert sorted(str(path.relative_to(OURS)) for path in OURS.rglob("*") if path.is_file()) == [
        "private/ButtonContent.qml"
    ]


def test_completing_the_module_links_every_other_file_and_drops_the_prefer_line(tmp_path):
    system = tmp_path / "system/components"
    (system / "private").mkdir(parents=True)
    (system / "qmldir").write_text(
        "module org.kde.plasma.components\nprefer :/qt/qml/org/kde/plasma/components/\nButton 3.0 Button.qml\n"
    )
    (system / "Button.qml").write_text("Button")
    (system / "private/ButtonContent.qml").write_text("theirs")
    (system / "private/IconLabel.qml").write_text("IconLabel")
    ours = tmp_path / "ours/components"
    (ours / "private").mkdir(parents=True)
    (ours / "private/ButtonContent.qml").write_text("ours")
    run_bash_with_steps(
        tmp_path,
        f"SETUP_DRY_RUN=0; MANIFEST={tmp_path}/manifest; STATE_DIR={tmp_path}; complete_qml_module {system} {ours}",
    )

    assert (
        (ours / "qmldir").read_text(),
        os.readlink(ours / "Button.qml"),
        os.readlink(ours / "private/IconLabel.qml"),
        (ours / "private/ButtonContent.qml").read_text(),
        (ours / "private/ButtonContent.qml").is_symlink(),
    ) == (
        "module org.kde.plasma.components\nButton 3.0 Button.qml\n",
        str(system / "Button.qml"),
        str(system / "private/IconLabel.qml"),
        "ours",
        False,
    )
