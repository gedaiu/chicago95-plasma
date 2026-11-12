/*
 * One user tile of the Welcome screen, measured from tests/references/xplogin.png (selected tile: x=425, y=253).
 *
 * Fitted gradients (3-sample moving average, fewest linear stops within 12 per channel):
 *
 *   frame      the 1px outline, row 253 of the tile at columns 430..799: #9CB2EA fading into the sky #5A7EDC
 *              by the middle of the tile, 2 stops
 *   fill       rows 256..259 averaged, columns 430..799: #1242A6 to column 514, then a straight ramp to the sky,
 *              3 stops (max deviation 6.0); the tile is 70px tall
 *   go button  rows 305..326 averaged over columns 670..672 and 688..690: a vertical green gradient, 3 stops
 */
import QtQuick 2.15
import QtQuick.Shapes 1.15

Item {
    id: tile

    property string name
    property url picture
    property bool selected
    property string status: ""  // in place of the password box, while Windows logs the user on
    readonly property bool askingPassword: selected && status === ""
    property int failureCount
    property string family: "Trebuchet MS"
    readonly property alias password: passwordInput.text
    readonly property real unit: parent && parent.unit ? parent.unit : 1

    signal chosen
    signal passwordAccepted(string password)

    width: 365 * unit
    height: (selected ? 70 : 63) * unit

    onSelectedChanged: {
        passwordInput.text = "";
        if (selected)
            passwordInput.forceActiveFocus();
    }
    onFailureCountChanged: {
        passwordInput.text = "";
        if (selected)
            passwordInput.forceActiveFocus();
    }

    Rectangle {
        id: edge
        anchors.fill: parent
        radius: 8 * tile.unit
        opacity: tile.selected || hover.hovered ? 1 : 0
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
                position: 0
                color: "#9cb2ea"
            }
            GradientStop {
                position: 0.5
                color: "#5a7edc"
            }
        }
    }
    Rectangle {
        x: tile.unit
        y: tile.unit
        width: parent.width - tile.unit
        height: parent.height - 2 * tile.unit
        radius: 8 * tile.unit
        opacity: tile.selected ? 1 : hover.hovered ? 0.55 : 0
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop {
                position: 0
                color: "#1242a6"
            }
            GradientStop {
                position: 0.244
                color: "#1242a6"
            }
            GradientStop {
                position: 1
                color: "#577bd9"
            }
        }
    }

    Rectangle {
        objectName: "avatarFrame"
        x: 10 * tile.unit
        y: 10 * tile.unit
        width: 52 * tile.unit
        height: 52 * tile.unit
        radius: 3 * tile.unit
        color: "#ffb600"
        Rectangle {
            x: tile.unit
            y: tile.unit
            width: parent.width - 2 * tile.unit
            height: parent.height - tile.unit
            radius: 2 * tile.unit
            color: "#ffee00"
        }
        Rectangle {
            id: face
            x: 2 * tile.unit
            y: 2 * tile.unit
            width: 48 * tile.unit
            height: 48 * tile.unit
            clip: true
            gradient: Gradient {
                GradientStop {
                    position: 0
                    color: "#4c9be6"
                }
                GradientStop {
                    position: 1
                    color: "#1b4fa8"
                }
            }
            Rectangle {
                x: 15 * tile.unit
                y: 8 * tile.unit
                width: 18 * tile.unit
                height: 18 * tile.unit
                radius: width / 2
                color: "#ffffff"
            }
            Rectangle {
                x: 8 * tile.unit
                y: 30 * tile.unit
                width: 32 * tile.unit
                height: 30 * tile.unit
                radius: 14 * tile.unit
                color: "#ffffff"
            }
            Image {
                objectName: "avatarImage"
                anchors.fill: parent
                source: tile.picture
                fillMode: Image.PreserveAspectCrop
            }
        }
    }

    Text {
        x: 75 * tile.unit
        y: (tile.selected ? 8 : 22) * tile.unit
        text: tile.name
        color: "#ffffff"
        font.family: tile.family
        font.pixelSize: 16 * tile.unit
    }
    Text {
        visible: tile.selected
        x: 75 * tile.unit
        y: 34 * tile.unit
        text: tile.status || "Type your password"
        color: "#ffffff"
        font.family: tile.family
        font.pixelSize: 11 * tile.unit
    }

    Rectangle {
        visible: tile.askingPassword
        x: 72 * tile.unit
        y: 52 * tile.unit
        width: 161 * tile.unit
        height: 27 * tile.unit
        radius: 3 * tile.unit
        color: "#00338f"
        opacity: 0.49
    }
    Rectangle {
        visible: tile.askingPassword
        x: 72 * tile.unit
        y: 51 * tile.unit
        width: 161 * tile.unit
        height: 27 * tile.unit
        radius: 3 * tile.unit
        color: "#00338f"
        opacity: 0.45
    }
    Rectangle {
        id: field
        visible: tile.askingPassword
        x: 71 * tile.unit
        y: 50 * tile.unit
        width: 161 * tile.unit
        height: 27 * tile.unit
        radius: 3 * tile.unit
        color: "#ffffff"
        TextInput {
            id: passwordInput
            objectName: "passwordInput"
            anchors.fill: parent
            anchors.margins: 4 * tile.unit
            verticalAlignment: TextInput.AlignVCenter
            echoMode: TextInput.Password
            passwordCharacter: "\u25cf"
            font.family: tile.family
            font.pixelSize: 13 * tile.unit
            color: "#000000"
            clip: true
            Keys.onReturnPressed: tile.passwordAccepted(text)
            Keys.onEnterPressed: tile.passwordAccepted(text)
        }
    }
    Rectangle {
        visible: tile.askingPassword
        x: 246 * tile.unit
        y: 53 * tile.unit
        width: 24 * tile.unit
        height: 24 * tile.unit
        radius: 3 * tile.unit
        color: "#002a85"
        opacity: 0.65
    }
    Rectangle {
        visible: tile.askingPassword
        x: 245 * tile.unit
        y: 52 * tile.unit
        width: 24 * tile.unit
        height: 24 * tile.unit
        radius: 3 * tile.unit
        color: "#002a85"
        opacity: 0.57
    }
    Rectangle {
        id: goButton
        visible: tile.askingPassword
        x: 244 * tile.unit
        y: 51 * tile.unit
        width: 24 * tile.unit
        height: 24 * tile.unit
        radius: 3 * tile.unit
        border.width: tile.unit
        border.color: "#ffffff"
        color: "#177417"
        Rectangle {
            x: tile.unit
            y: 1 * tile.unit
            width: parent.width - 2 * tile.unit
            height: 3 * tile.unit
            radius: 2 * tile.unit
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0.0
                    color: "#6cb56c"
                }
                GradientStop {
                    position: 0.19
                    color: "#6db66d"
                }
                GradientStop {
                    position: 0.381
                    color: "#57ab57"
                }
                GradientStop {
                    position: 0.571
                    color: "#4fa74f"
                }
                GradientStop {
                    position: 0.762
                    color: "#40a040"
                }
                GradientStop {
                    position: 1.0
                    color: "#388438"
                }
            }
        }
        Rectangle {
            x: tile.unit
            y: 4 * tile.unit
            width: parent.width - 2 * tile.unit
            height: 3 * tile.unit
            radius: 0 * tile.unit
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0.0
                    color: "#4fa74f"
                }
                GradientStop {
                    position: 0.19
                    color: "#77bb77"
                }
                GradientStop {
                    position: 0.381
                    color: "#5cac5c"
                }
                GradientStop {
                    position: 0.571
                    color: "#4fa74f"
                }
                GradientStop {
                    position: 0.762
                    color: "#3c9e3c"
                }
                GradientStop {
                    position: 1.0
                    color: "#176a17"
                }
            }
        }
        Rectangle {
            x: tile.unit
            y: 7 * tile.unit
            width: parent.width - 2 * tile.unit
            height: 3 * tile.unit
            radius: 0 * tile.unit
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0.0
                    color: "#41a041"
                }
                GradientStop {
                    position: 0.19
                    color: "#64b164"
                }
                GradientStop {
                    position: 0.381
                    color: "#4ba34b"
                }
                GradientStop {
                    position: 0.571
                    color: "#369b36"
                }
                GradientStop {
                    position: 0.762
                    color: "#289828"
                }
                GradientStop {
                    position: 1.0
                    color: "#196d19"
                }
            }
        }
        Rectangle {
            x: tile.unit
            y: 10 * tile.unit
            width: parent.width - 2 * tile.unit
            height: 3 * tile.unit
            radius: 0 * tile.unit
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0.0
                    color: "#349934"
                }
                GradientStop {
                    position: 0.19
                    color: "#52aa52"
                }
                GradientStop {
                    position: 0.381
                    color: "#45a645"
                }
                GradientStop {
                    position: 0.571
                    color: "#38a338"
                }
                GradientStop {
                    position: 0.762
                    color: "#2a9f2a"
                }
                GradientStop {
                    position: 1.0
                    color: "#146d14"
                }
            }
        }
        Rectangle {
            x: tile.unit
            y: 13 * tile.unit
            width: parent.width - 2 * tile.unit
            height: 3 * tile.unit
            radius: 0 * tile.unit
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0.0
                    color: "#259225"
                }
                GradientStop {
                    position: 0.19
                    color: "#52a852"
                }
                GradientStop {
                    position: 0.381
                    color: "#49a749"
                }
                GradientStop {
                    position: 0.571
                    color: "#33ac33"
                }
                GradientStop {
                    position: 0.762
                    color: "#1dae1d"
                }
                GradientStop {
                    position: 1.0
                    color: "#0c6d0c"
                }
            }
        }
        Rectangle {
            x: tile.unit
            y: 16 * tile.unit
            width: parent.width - 2 * tile.unit
            height: 3 * tile.unit
            radius: 0 * tile.unit
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0.0
                    color: "#168b16"
                }
                GradientStop {
                    position: 0.19
                    color: "#44a244"
                }
                GradientStop {
                    position: 0.381
                    color: "#41a541"
                }
                GradientStop {
                    position: 0.571
                    color: "#36b236"
                }
                GradientStop {
                    position: 0.762
                    color: "#17b517"
                }
                GradientStop {
                    position: 1.0
                    color: "#036903"
                }
            }
        }
        Rectangle {
            x: tile.unit
            y: 19 * tile.unit
            width: parent.width - 2 * tile.unit
            height: 2 * tile.unit
            radius: 0 * tile.unit
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0.0
                    color: "#0c820c"
                }
                GradientStop {
                    position: 0.19
                    color: "#309630"
                }
                GradientStop {
                    position: 0.381
                    color: "#309a30"
                }
                GradientStop {
                    position: 0.571
                    color: "#22a422"
                }
                GradientStop {
                    position: 0.762
                    color: "#0eaa0e"
                }
                GradientStop {
                    position: 1.0
                    color: "#006300"
                }
            }
        }
        Rectangle {
            x: tile.unit
            y: 21 * tile.unit
            width: parent.width - 2 * tile.unit
            height: 2 * tile.unit
            radius: 2 * tile.unit
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0.0
                    color: "#448e44"
                }
                GradientStop {
                    position: 0.19
                    color: "#177417"
                }
                GradientStop {
                    position: 0.381
                    color: "#187618"
                }
                GradientStop {
                    position: 0.571
                    color: "#107c10"
                }
                GradientStop {
                    position: 0.762
                    color: "#067a06"
                }
                GradientStop {
                    position: 1.0
                    color: "#3f813f"
                }
            }
        }
        Rectangle {
            x: 4 * tile.unit
            y: 10 * tile.unit
            width: 16 * tile.unit
            height: 3 * tile.unit
            color: "#ffffff"
        }
        Rectangle {
            x: (15 - 4.5) * tile.unit
            y: (8.2 - 1.5) * tile.unit
            width: 9 * tile.unit
            height: 3 * tile.unit
            rotation: 45
            color: "#ffffff"
        }
        Rectangle {
            x: (15 - 4.5) * tile.unit
            y: (15.6 - 1.5) * tile.unit
            width: 9 * tile.unit
            height: 3 * tile.unit
            rotation: -45
            color: "#ffffff"
        }
        MouseArea {
            anchors.fill: parent
            onClicked: tile.passwordAccepted(passwordInput.text)
        }
    }

    HoverHandler {
        id: hover
    }
    TapHandler {
        enabled: !tile.selected
        onTapped: tile.chosen()
    }
}
