/*
 * The Windows XP "Welcome" screen at 800x600, the layout measured from tests/references/xplogin.png.
 *
 * Fitted gradients. The screenshot is JPEG-like quantised, so every profile was averaged over text-free
 * columns or rows, smoothed with a 3-sample moving average, and reduced to the fewest linear stops that stay
 * within 12 per channel of that average (positions are fractions of the 800px width or the 424px middle band):
 *
 *   top rule rows 78 and 79         columns 0..799 of each row, 4 stops each (max deviation 6.0 and 6.0)
 *   bottom rule rows 504 and 505    columns 0..799 of each row, 6 stops each (max deviation 8.0 and 9.0)
 *   bottom band                     rows 562..574 averaged, columns 0..799, 2 stops (max deviation 1.0)
 *   divider                         column 398, rows 80..503, 3 stops (max deviation 7.0)
 *   glow                            white alpha over the sky, rows 80..329, columns 0..299: the centre (60, 120)
 *                                   minimises the residual of the radial profile, which is a straight ramp from
 *                                   alpha 0.38 at the centre to 0 at radius 165, 2 stops (max deviation 6.5 along row 100, 7.5 down column 60)
 */
pragma ComponentBehavior: Bound
import QtQuick 2.15
import QtQuick.Shapes 1.15
import "../qml"

Item {
    id: root

    property var greeter
    property var users
    property var sessions
    property var theme: ({})
    property var keyboardState: null
    property bool shuttingDown: false
    property bool locked: false
    property string family: "Trebuchet MS"

    readonly property real unit: height / 600
    readonly property real topBandHeight: 78 * unit
    readonly property real bottomBandTop: height - 96 * unit
    readonly property real middleCenterY: (80 * unit + bottomBandTop) / 2
    readonly property real dividerX: width / 2 - 2 * unit
    readonly property color skyBlue: "#5a7edc"
    readonly property color bandBlue: "#00309c"

    property string selectedName: users ? users.lastUser : ""
    property int sessionIndex: sessions ? Math.max(0, sessions.lastIndex) : 0
    property int failureCount: 0
    property string message: ""
    readonly property var sessionNames: namesOf(sessionRepeater)

    function namesOf(repeater) {
        const names = [];
        for (let index = 0; index < repeater.count; index++)
            names.push(repeater.itemAt(index).label);
        return names;
    }

    function logIn(userName, password) {
        message = "";
        greeter.login(userName, password, sessionIndex);
    }

    Connections {
        target: root.greeter
        function onLoginFailed() {
            root.message = "The password is incorrect. Try again.";
            root.failureCount++;
        }
    }

    Repeater {
        id: sessionRepeater
        model: root.sessions
        delegate: Item {
            id: sessionEntry
            required property var model
            readonly property string label: model.name
        }
    }

    Rectangle {
        anchors.fill: parent
        color: root.skyBlue
    }

    Item {
        id: middleBand
        y: 80 * root.unit
        width: parent.width
        height: root.bottomBandTop - y
        clip: true
        Shape {
            width: 230 * root.unit
            height: 210 * root.unit
            ShapePath {
                strokeColor: "transparent"
                fillGradient: RadialGradient {
                    centerX: 60 * root.unit
                    centerY: 40 * root.unit
                    centerRadius: 165 * root.unit
                    focalX: centerX
                    focalY: centerY
                    GradientStop {
                        position: 0
                        color: "#61ffffff"
                    }
                    GradientStop {
                        position: 1
                        color: "#00ffffff"
                    }
                }
                startX: 0
                startY: 0
                PathLine {
                    x: 230 * root.unit
                    y: 0
                }
                PathLine {
                    x: 230 * root.unit
                    y: 210 * root.unit
                }
                PathLine {
                    x: 0
                    y: 210 * root.unit
                }
            }
        }
    }

    Rectangle {
        id: divider
        visible: !root.shuttingDown
        x: root.dividerX
        y: 80 * root.unit
        width: Math.max(1, root.unit)
        height: root.bottomBandTop - y
        gradient: Gradient {
            GradientStop {
                position: 0
                color: "#5a7edc"
            }
            GradientStop {
                position: 0.504
                color: "#91aeee"
            }
            GradientStop {
                position: 1
                color: "#5a7edc"
            }
        }
    }

    Rectangle {
        width: parent.width
        height: root.topBandHeight
        color: root.bandBlue
    }
    Rectangle {
        y: root.topBandHeight
        width: parent.width
        height: Math.max(1, root.unit)
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
                position: 0
                color: "#4b72d0"
            }
            GradientStop {
                position: 0.219
                color: "#c2dafd"
            }
            GradientStop {
                position: 0.37
                color: "#c2d8fd"
            }
            GradientStop {
                position: 1
                color: "#4a72d0"
            }
        }
    }
    Rectangle {
        y: root.topBandHeight + Math.max(1, root.unit)
        width: parent.width
        height: Math.max(1, root.unit)
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
                position: 0
                color: "#5a7edc"
            }
            GradientStop {
                position: 0.223
                color: "#c5dbfe"
            }
            GradientStop {
                position: 0.334
                color: "#c5dbfe"
            }
            GradientStop {
                position: 1
                color: "#5a7edc"
            }
        }
    }

    Rectangle {
        id: bottomBand
        y: root.bottomBandTop
        width: parent.width
        height: parent.height - y
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
                position: 0
                color: "#3834ac"
            }
            GradientStop {
                position: 1
                color: "#00309c"
            }
        }
    }
    Rectangle {
        y: root.bottomBandTop
        width: parent.width
        height: Math.max(1, root.unit)
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
                position: 0
                color: "#0c369d"
            }
            GradientStop {
                position: 0.02
                color: "#0c369e"
            }
            GradientStop {
                position: 0.214
                color: "#f29139"
            }
            GradientStop {
                position: 0.3517
                color: "#f69733"
            }
            GradientStop {
                position: 0.9549
                color: "#093597"
            }
            GradientStop {
                position: 1
                color: "#1242a8"
            }
        }
    }
    Rectangle {
        y: root.bottomBandTop + Math.max(1, root.unit)
        width: parent.width
        height: Math.max(1, root.unit)
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
                position: 0
                color: "#083799"
            }
            GradientStop {
                position: 0.0125
                color: "#032f92"
            }
            GradientStop {
                position: 0.2153
                color: "#f69437"
            }
            GradientStop {
                position: 0.3454
                color: "#f99634"
            }
            GradientStop {
                position: 0.9637
                color: "#053292"
            }
            GradientStop {
                position: 1
                color: "#002ea0"
            }
        }
    }

    XpWordmark {
        id: wordmark
        x: root.shuttingDown ? root.width / 2 + 39 * root.unit : root.dividerX - 21 * root.unit - wordmark.width
        y: root.middleCenterY - 59 * root.unit
        unit: root.unit
        family: root.family
        // The branding Setup writes into theme.conf; the logo is a file next to the theme (brand-logo.*).
        name: root.theme.brandText || ""
        company: root.theme.company || ""
        edition: root.theme.brandText ? root.theme.edition || "" : ""
        logo: !root.theme.brandLogo ? "" : String(root.theme.brandLogo).indexOf("/") === 0 ? root.theme.brandLogo : Qt.resolvedUrl("../../" + root.theme.brandLogo)
    }

    Text {
        x: (root.shuttingDown ? root.width / 2 + 33 * root.unit : root.dividerX - 171.5 * root.unit) - width / 2
        y: root.middleCenterY + (root.shuttingDown ? 44 : 44) * root.unit
        text: root.shuttingDown ? "Windows is shutting down..." : root.locked ? "To unlock, type your password" : "To begin, click your user name"
        color: "#ffffff"
        font.family: root.family
        font.pixelSize: 16 * root.unit
    }

    Repeater {
        id: userRepeater
        model: root.shuttingDown ? null : root.users
        delegate: Item {
            id: userEntry
            required property var model
            readonly property string label: model.name
        }
    }

    Column {
        id: tiles
        visible: !root.shuttingDown
        readonly property real unit: root.unit
        x: root.dividerX + 27 * root.unit
        y: root.middleCenterY - 39.5 * root.unit
        spacing: 10 * root.unit
        Repeater {
            model: root.shuttingDown ? null : root.users
            delegate: LunaUserTile {
                id: userTile
                required property var model
                name: model.realName || model.name
                picture: model.icon || ""
                selected: model.name === root.selectedName
                failureCount: root.failureCount
                family: root.family
                onChosen: root.selectedName = model.name
                onPasswordAccepted: password => root.logIn(model.name, password)
            }
        }
    }

    Text {
        visible: !root.shuttingDown && root.message !== ""
        x: tiles.x + 75 * root.unit
        y: root.middleCenterY + 48 * root.unit
        text: root.message
        color: "#ffffff"
        font.family: root.family
        font.pixelSize: 11 * root.unit
    }
    Text {
        visible: !root.shuttingDown && !!root.keyboardState && root.keyboardState.capsLock
        x: tiles.x + 75 * root.unit
        y: root.middleCenterY + 64 * root.unit
        text: "Caps Lock is on"
        color: "#ffffff"
        font.family: root.family
        font.pixelSize: 11 * root.unit
    }

    Item {
        id: bottomContent
        visible: !root.shuttingDown
        readonly property bool hasPowerActions: powerChoices.names.length > 0
        y: root.bottomBandTop

        Rectangle {
            id: powerIcon
            visible: bottomContent.hasPowerActions
            x: 25 * root.unit
            y: 23 * root.unit
            width: 22 * root.unit
            height: 22 * root.unit
            radius: 3 * root.unit
            border.width: root.unit
            border.color: "#ffffff"
            gradient: Gradient {
                GradientStop {
                    position: 0
                    color: "#e7785a"
                }
                GradientStop {
                    position: 1
                    color: "#ce441d"
                }
            }
            Shape {
                anchors.centerIn: parent
                width: 12 * root.unit
                height: 12 * root.unit
                ShapePath {
                    strokeColor: "#ffffff"
                    strokeWidth: 2 * root.unit
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap
                    startX: 6 * root.unit
                    startY: 0
                    PathLine {
                        x: 6 * root.unit
                        y: 5 * root.unit
                    }
                }
                ShapePath {
                    strokeColor: "#ffffff"
                    strokeWidth: 2 * root.unit
                    fillColor: "transparent"
                    capStyle: ShapePath.RoundCap
                    startX: 3 * root.unit
                    startY: 2.5 * root.unit
                    PathArc {
                        x: 9 * root.unit
                        y: 2.5 * root.unit
                        radiusX: 5 * root.unit
                        radiusY: 5 * root.unit
                        useLargeArc: true
                        direction: PathArc.Counterclockwise
                    }
                }
            }
        }
        Text {
            id: turnOffLabel
            visible: bottomContent.hasPowerActions
            x: 55 * root.unit
            y: 23 * root.unit
            text: "Turn off computer"
            color: "#ffffff"
            font.family: root.family
            font.pixelSize: 17 * root.unit
        }
        MouseArea {
            enabled: bottomContent.hasPowerActions
            x: powerIcon.x
            y: powerIcon.y
            width: turnOffLabel.x + turnOffLabel.width - powerIcon.x
            height: powerIcon.height
            onClicked: powerChoices.visible = !powerChoices.visible
        }
        Text {
            x: root.width - 330 * root.unit
            y: 23 * root.unit
            lineHeight: 1.1
            visible: !root.locked
            text: "After you log on, you can add or change accounts.\nJust go to Control Panel and click User Accounts."
            color: "#ffffff"
            font.family: root.family
            font.pixelSize: 11 * root.unit
        }
        Text {
            id: sessionLink
            visible: !root.locked
            x: root.width - 330 * root.unit
            y: 75 * root.unit
            text: "Session: " + (root.sessionNames[root.sessionIndex] || "")
            color: "#c7ddff"
            font.family: root.family
            font.pixelSize: 10 * root.unit
            font.underline: true
            MouseArea {
                anchors.fill: parent
                onClicked: sessionChoices.visible = !sessionChoices.visible
            }
        }
    }

    component ChoiceList: Column {
        id: choiceList
        property var names: []
        signal picked(int index)
        visible: false
        Repeater {
            model: choiceList.names
            delegate: Rectangle {
                id: choice
                required property string modelData
                required property int index
                width: 150 * root.unit
                height: 22 * root.unit
                color: pick.containsMouse ? "#316ac5" : "#ece9d8"
                Text {
                    x: 8 * root.unit
                    anchors.verticalCenter: parent.verticalCenter
                    text: choice.modelData
                    color: pick.containsMouse ? "#ffffff" : "#000000"
                    font.family: root.family
                    font.pixelSize: 11 * root.unit
                }
                MouseArea {
                    id: pick
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        choiceList.visible = false;
                        choiceList.picked(choice.index);
                    }
                }
            }
        }
    }

    ChoiceList {
        id: powerChoices
        x: 25 * root.unit
        y: root.bottomBandTop - height - 4 * root.unit
        readonly property var actions: root.locked ? [] : [() => root.greeter.powerOff(), () => root.greeter.reboot()]
        names: (root.locked ? [] : ["Turn Off", "Restart"]).concat(root.greeter && root.greeter.canSuspend ? ["Stand By"] : [])
        onPicked: index => actions.concat([() => root.greeter.suspend()])[index]()
    }
    ChoiceList {
        id: sessionChoices
        x: root.width - 330 * root.unit
        y: root.bottomBandTop + 72 * root.unit - height
        names: root.sessionNames
        onPicked: index => root.sessionIndex = index
    }

    Component.onCompleted: if (selectedName === "" && userRepeater.count > 0)
        selectedName = userRepeater.itemAt(0).label
}
