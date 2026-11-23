import QtQuick
import org.kde.kwin.decoration
import org.kde.ksvg as KSvg
import "."
import "Theme.js" as Theme

SystemAurorae {
    id: frame
    readonly property real outputScale: decoration.client.scale || 1
    readonly property bool classicCaptionAt120Dpi: auroraeTheme.followsScheme && outputScale === 1.25
    readonly property var buttonGroups: children.filter(item =>
        item.animate !== undefined && item.buttons !== undefined)
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

    // Paint the caption SVG elements on the output's pixel grid. Keep
    // Aurorae's button positions, input handling and state transitions.
    Repeater {
        model: frame.classicCaptionAt120Dpi || (frame.auroraeTheme.alignCaptionPixels && frame.outputScale % 1 !== 0) ? 2 : 0
        delegate: Item {
            id: groupDelegate
            required property int index
            readonly property Item group: frame.buttonGroups[index] ?? null
            readonly property Item row: group?.children[0] ?? null
            readonly property var faces: {
                const types = [DecorationOptions.DecorationButtonMinimize, DecorationOptions.DecorationButtonClose,
                               DecorationOptions.DecorationButtonMaximizeRestore,
                               DecorationOptions.DecorationButtonMaximizeRestore + 100]
                const states = []
                for (const item of row?.children ?? []) {
                    for (const control of item.buttonType === undefined ? item.children : [item]) {
                        if (types.includes(control.buttonType)) {
                            for (const child of control.children) {
                                if (child instanceof KSvg.FrameSvgItem)
                                    states.push(child)
                            }
                        }
                    }
                }
                return states
            }
            Repeater {
                model: groupDelegate.faces
                delegate: Item {
                    id: stateDelegate
                    required property Item modelData
                    readonly property Item control: modelData.parent
                    readonly property point origin: {
                        let left = 0
                        let top = 0
                        for (let item = control; item && item !== frame; item = item.parent) {
                            left += item.x
                            top += item.y
                        }
                        return Qt.point(left, top)
                    }
                    Binding {
                        target: stateDelegate.modelData
                        property: "visible"
                        value: false
                    }
                    KSvg.SvgItem {
                        x: Math.round(stateDelegate.origin.x * frame.outputScale) / frame.outputScale
                        y: Math.round(stateDelegate.origin.y * frame.outputScale) / frame.outputScale
                        // KSvg multiplies the requested size by the output DPR.
                        // Classic has a device-size master for this scale.
                        width: frame.classicCaptionAt120Dpi
                            ? Math.ceil(stateDelegate.control.width * frame.outputScale) / frame.outputScale
                            : Math.ceil(stateDelegate.control.width * frame.outputScale)
                        height: frame.classicCaptionAt120Dpi
                            ? Math.ceil(stateDelegate.control.height * frame.outputScale) / frame.outputScale
                            : Math.ceil(stateDelegate.control.height * frame.outputScale)
                        scale: frame.classicCaptionAt120Dpi ? 1 : 1 / frame.outputScale
                        transformOrigin: Item.TopLeft
                        smooth: false
                        imagePath: frame.classicCaptionAt120Dpi
                            ? stateDelegate.modelData.imagePath.replace(/\.svg$/, "-120.svg")
                            : stateDelegate.modelData.imagePath
                        elementId: stateDelegate.modelData.prefix + "-center"
                        opacity: stateDelegate.modelData.opacity * stateDelegate.control.opacity
                        visible: opacity > 0 && stateDelegate.control.visible
                    }
                }
            }
        }
    }

    // Aurorae keeps the disabled face, but its maximize wrapper also has an
    // independent MouseArea. Disable that area so it cannot paint hover or press.
    Repeater {
        model: 2
        delegate: Item {
            required property int index
            readonly property Item group: frame.buttonGroups[index] ?? null
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
