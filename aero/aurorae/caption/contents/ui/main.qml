// The qmldir maps SystemAurorae to the distribution's installed Aurorae renderer.
import QtQuick
import Qt5Compat.GraphicalEffects
import org.kde.kwin.decoration
import "."
import "Theme.js" as Theme

SystemAurorae {
    id: frame
    readonly property var auroraeTheme: Theme.metrics(decorationSettings.borderSize,
                                                     decoration.readConfig("ButtonSize", 1))
    readonly property Item titleLabel: children.find(item => item.elide !== undefined
                                                          && item.textFormat !== undefined) ?? null
    readonly property Item menuGroup: children.find(item => item.buttons?.length === 1
                                                         && item.buttons[0] === DecorationOptions.DecorationButtonMenu) ?? null

    Binding {
        target: frame.menuGroup
        property: "anchors.topMargin"
        when: frame.menuGroup !== null
        value: frame.titleLabel ? frame.titleLabel.y + Math.round((frame.titleLabel.height - auroraeTheme.buttonHeight * auroraeTheme.buttonSizeFactor) / 2) : 0
    }

    Glow {
        parent: frame.titleLabel
        visible: parent && parent.text.length > 0
        anchors.left: parent ? parent.left : undefined
        anchors.verticalCenter: parent ? parent.verticalCenter : undefined
        width: parent ? Math.min(parent.width, Math.ceil(parent.contentWidth)) : 0
        height: parent ? parent.height : 0
        z: -1
        radius: 9
        samples: 19
        opacity: 0.65
        spread: 0.65
        color: "white"
        transparentBorder: true
        cached: true
        source: Text {
            width: frame.titleLabel ? Math.min(frame.titleLabel.width, Math.ceil(frame.titleLabel.contentWidth)) : 0
            height: frame.titleLabel?.height ?? 0
            text: frame.titleLabel?.text ?? ""
            font: frame.titleLabel ? frame.titleLabel.font : Qt.font({})
            textFormat: Text.PlainText
            renderType: Text.NativeRendering
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            color: "white"
            visible: false
        }
    }
}
