import QtQuick
import org.kde.kwin.decoration
import "."
import "Theme.js" as Theme

SystemAurorae {
    id: frame
    readonly property var auroraeTheme: {
        const theme = Theme.metrics(decorationSettings.borderSize, decoration.readConfig("ButtonSize", 1));
        if (theme.followsScheme && !decoration.client.active)
            theme.inactiveTextColor = scheme.fontColor;
        return theme;
    }
    DecorationOptions {
        id: scheme
        deco: decoration
    }
    readonly property Item caption: children.find(item => item.elide !== undefined
                                                       && item.textFormat !== undefined) ?? null
    Loader {
        parent: frame.caption ?? frame
        z: -1
        width: frame.caption?.width ?? 0
        height: frame.caption?.height ?? 0
        x: frame.auroraeTheme.textShadowX ?? 0
        y: frame.auroraeTheme.textShadowY ?? 0
        active: frame.caption !== null && frame.auroraeTheme.useTextShadow
        sourceComponent: Text {
            text: frame.caption.text
            font: frame.caption.font
            elide: frame.caption.elide
            horizontalAlignment: frame.caption.horizontalAlignment
            verticalAlignment: frame.caption.verticalAlignment
            textFormat: Text.PlainText
            renderType: Text.NativeRendering
            color: decoration.client.active ? frame.auroraeTheme.activeTextShadowColor
                                            : frame.auroraeTheme.inactiveTextShadowColor
        }
    }

    // Aurorae keeps the disabled face, but its maximize wrapper also has an
    // independent MouseArea. Disable that area so it cannot paint hover or press.
    Repeater {
        model: 2
        delegate: Item {
            required property int index
            readonly property Item group: frame.children.filter(item =>
                item.animate !== undefined && item.buttons !== undefined)[index] ?? null
            readonly property Item maximize: group?.children[0]?.children.find(item =>
                item.children[0]?.buttonType === DecorationOptions.DecorationButtonMaximizeRestore) ?? null
            Binding {
                target: parent.maximize?.children.find(item => item instanceof MouseArea) ?? null
                property: "enabled"
                value: decoration.client.maximizeable
                when: target !== null
            }
        }
    }
}
