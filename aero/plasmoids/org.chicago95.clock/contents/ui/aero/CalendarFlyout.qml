import QtQuick
import QtQuick.Controls.Basic as Controls
import QtQuick.Layouts

Rectangle {
    id: calendar
    property date now: new Date()
    property date month: new Date(now.getFullYear(), now.getMonth(), 1)
    signal settingsRequested()
    implicitWidth: 340
    implicitHeight: 222
    color: "#fbfcfd"
    border.color: "#a5b8c6"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 4
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: Qt.formatDate(calendar.now, Qt.locale().dateFormat(Locale.LongFormat))
            color: "#184e82"
        }
        RowLayout {
            Layout.fillHeight: true
            ColumnLayout {
                spacing: 0
                RowLayout {
                    Controls.ToolButton {
                        text: "‹"
                        Accessible.name: qsTr("Previous month")
                        onClicked: calendar.month = new Date(calendar.month.getFullYear(), calendar.month.getMonth() - 1, 1)
                    }
                    Text { Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; text: Qt.formatDate(calendar.month, "MMMM yyyy"); color: "#121d29" }
                    Controls.ToolButton {
                        text: "›"
                        Accessible.name: qsTr("Next month")
                        onClicked: calendar.month = new Date(calendar.month.getFullYear(), calendar.month.getMonth() + 1, 1)
                    }
                }
                Controls.DayOfWeekRow { Layout.fillWidth: true; Layout.preferredHeight: 18; palette.windowText: "#152539" }
                Controls.MonthGrid {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    month: calendar.month.getMonth()
                    year: calendar.month.getFullYear()
                    palette.windowText: "#152539"
                }
            }
            Rectangle {
                id: dial
                Layout.preferredWidth: 86
                Layout.preferredHeight: 86
                radius: 43
                color: "#f6f8fa"
                border.width: 2
                border.color: "#7790a0"
                Repeater {
                    model: 12
                    Item {
                        required property int index
                        anchors.fill: parent
                        rotation: index * 30
                        Rectangle { anchors.horizontalCenter: parent.horizontalCenter; y: 4; width: 2; height: 5; color: "#475563" }
                    }
                }
                Repeater {
                    model: [calendar.now.getHours() * 30 + calendar.now.getMinutes() / 2, calendar.now.getMinutes() * 6, calendar.now.getSeconds() * 6]
                    Item {
                        required property real modelData
                        required property int index
                        anchors.fill: parent
                        rotation: modelData
                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.verticalCenter
                            width: index === 2 ? 1 : 3
                            height: index === 0 ? 21 : 32
                            color: index === 2 ? "#b54737" : "#223646"
                        }
                    }
                }
            }
        }
        Controls.ToolButton {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("Change date and time settings…")
            onClicked: calendar.settingsRequested()
        }
    }
}
