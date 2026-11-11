"""Stand-ins for the screencast QML modules a task tooltip's live preview uses (org.kde.pipewire,
org.kde.taskmanager): a solid blue square in place of the stream. Every engine that loads a tooltip gets the
folder as an import path: QML registers a module's plugin once per process, so the first engine to load the
real modules would fix them for every later test."""

STUBS = {
    "org/kde/pipewire/qmldir": "module org.kde.pipewire\nPipeWireSourceItem 1.0 PipeWireSourceItem.qml\n",
    "org/kde/pipewire/PipeWireSourceItem.qml": "import QtQuick\nRectangle { property var nodeId; color: '#4080c0' }\n",
    "org/kde/taskmanager/qmldir": "module org.kde.taskmanager\nScreencastingRequest 1.0 ScreencastingRequest.qml\n",
    "org/kde/taskmanager/ScreencastingRequest.qml": (
        "import QtQuick\nQtObject { property string uuid; property int nodeId: 1 }\n"
    ),
}
PICTURE = (64, 128, 192)


def write_stubs(folder):
    for name, text in STUBS.items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(text)
    return folder
