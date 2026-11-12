import QtQuick 2.15

Item {
    id: wordmark

    property real unit: 1
    property string edition: ""
    property color textColor: "#ffffff"
    property string family: "Trebuchet MS"
    // The user's branding (Control Panel > Passwords > Branding): with a name, their logo, company, name and
    // edition take the Windows XP wordmark's place, laid out on its grid; without one, the wordmark itself.
    property string name: ""
    property string company: ""
    property string logo: ""

    readonly property bool branded: name !== ""
    readonly property real editionBaseline: 93.6
    readonly property real fullWidth: 132
    readonly property real logoAspect: 365.166 / 621.401
    readonly property real nameLeft: 44
    readonly property real nameBaseline: 44
    readonly property real brandedWidth: 220  // room for a name like "Windows2026" at full size

    implicitWidth: (branded ? brandedWidth : fullWidth) * unit
    implicitHeight: (branded ? 68 : edition === "" ? fullWidth * logoAspect : editionBaseline + 1) * unit

    Image {
        visible: wordmark.branded && wordmark.logo !== ""
        x: 0
        y: 4 * wordmark.unit
        width: 40 * wordmark.unit
        height: 36 * wordmark.unit
        fillMode: Image.PreserveAspectFit
        smooth: true
        sourceSize: Qt.size(width * 2, height * 2)
        source: wordmark.logo === "" ? "" : wordmark.logo.indexOf("/") === 0 ? "file://" + wordmark.logo : wordmark.logo
    }
    Text {
        visible: wordmark.branded && wordmark.company !== ""
        x: (wordmark.nameLeft + 2) * wordmark.unit
        y: 16 * wordmark.unit - baselineOffset
        text: wordmark.company
        color: wordmark.textColor
        font.family: wordmark.family
        font.pixelSize: 10 * wordmark.unit
    }
    Text {
        id: brandName
        visible: wordmark.branded
        x: wordmark.nameLeft * wordmark.unit
        y: wordmark.nameBaseline * wordmark.unit - baselineOffset
        width: (wordmark.brandedWidth - wordmark.nameLeft) * wordmark.unit
        fontSizeMode: Text.HorizontalFit
        minimumPixelSize: 8
        text: wordmark.name
        color: wordmark.textColor
        font.family: wordmark.family
        font.bold: true
        font.pixelSize: 26 * wordmark.unit
    }
    Text {
        visible: wordmark.branded && wordmark.edition !== ""
        x: brandName.x + brandName.contentWidth - width
        y: brandName.y + brandName.height  // right under the name, never into it
        text: wordmark.edition
        color: wordmark.textColor
        font.family: wordmark.family
        font.pixelSize: 14 * wordmark.unit
    }

    Image {
        visible: !wordmark.branded
        width: wordmark.fullWidth * wordmark.unit
        height: width * wordmark.logoAspect
        sourceSize: Qt.size(width, height)
        source: "../images/windows-xp-logo-light.svg"
    }

    Text {
        visible: !wordmark.branded && wordmark.edition !== ""
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
