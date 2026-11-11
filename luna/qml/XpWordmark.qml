import QtQuick 2.15

Item {
    id: wordmark

    property real unit: 1
    property string edition: ""
    property color textColor: "#ffffff"
    property string family: "Trebuchet MS"

    readonly property real editionBaseline: 93.6
    readonly property real fullWidth: 132
    readonly property real logoAspect: 365.166 / 621.401

    implicitWidth: fullWidth * unit
    implicitHeight: (edition === "" ? fullWidth * logoAspect : editionBaseline + 1) * unit

    Image {
        width: wordmark.fullWidth * wordmark.unit
        height: width * wordmark.logoAspect
        sourceSize: Qt.size(width, height)
        source: "../images/windows-xp-logo-light.svg"
    }

    Text {
        visible: wordmark.edition !== ""
        x: 8 * wordmark.unit
        y: wordmark.editionBaseline * wordmark.unit - baselineOffset
        width: 90 * wordmark.unit
        fontSizeMode: Text.HorizontalFit
        minimumPixelSize: 8
        text: wordmark.edition
        color: wordmark.textColor
        font.family: wordmark.family
        font.pixelSize: 18 * wordmark.unit
    }
}
