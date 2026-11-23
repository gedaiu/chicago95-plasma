// The qmldir maps SystemAurorae to the distribution's installed Aurorae renderer.
import QtQuick
import Qt5Compat.GraphicalEffects
import org.kde.kwin.decoration
import "."
import "Theme.js" as Theme

SystemAurorae {
    id: frame
    readonly property var auroraeTheme: Theme.metrics(decorationSettings.borderSize,
                                                     decoration.readConfig("ButtonSize", 1), decoration.client.scale)
    readonly property Item titleLabel: children.find(item => item.elide !== undefined
                                                          && item.textFormat !== undefined) ?? null
    readonly property Item menuGroup: children.find(item => item.buttons?.length === 1
                                                         && item.buttons[0] === DecorationOptions.DecorationButtonMenu) ?? null

    // Aurorae reserves the title width for the configured buttons. Use the themed
    // row when the group consists entirely of the Windows caption controls.
    Repeater {
        model: 2
        delegate: Loader {
            id: groupLoader
            required property int index
            readonly property Item group: frame.children.filter(item => item.animate !== undefined
                && item.buttons !== undefined)[index] ?? null
            active: group?.buttons?.length > 0 && Array.from(group.buttons).every(type =>
                [DecorationOptions.DecorationButtonMinimize, DecorationOptions.DecorationButtonMaximizeRestore,
                 DecorationOptions.DecorationButtonClose].includes(type))
            // Aurorae positions the row in logical units. At fractional scale its
            // upper border can fall halfway between two output pixels.
            readonly property real outputScale: decoration.client.scale || 1
            x: Math.round((group?.x ?? 0) * outputScale) / outputScale
            y: Math.round((group?.y ?? 0) * outputScale) / outputScale
            Binding { target: groupLoader.group; property: "visible"; value: false; when: groupLoader.active }
            sourceComponent: CaptionButtons {
                buttons: groupLoader.group.buttons
                theme: frame.auroraeTheme
            }
        }
    }

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
