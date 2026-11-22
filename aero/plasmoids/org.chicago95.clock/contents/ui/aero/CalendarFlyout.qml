import QtQuick
import QtQuick.Controls.Basic as Controls
import QtQuick.Layouts

Rectangle {
    id: calendar
    property date now: new Date()
    property date month: new Date(now.getFullYear(), now.getMonth(), 1)
    signal settingsRequested()
    implicitWidth: 336
    implicitHeight: 247
    color: "white"

    component Label: Text {
        font.family: "Segoe UI"
        font.pixelSize: 12
        color: "#101010"
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    Label {
        width: parent.width
        y: 10
        height: 23
        text: Qt.formatDate(calendar.now, Qt.locale().dateFormat(Locale.LongFormat))
        color: "#0066cc"
    }
    ColumnLayout {
        x: 14
        y: 47
        width: parent.width - 170
        height: 134
        spacing: 0
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 23
            Controls.ToolButton {
                text: "◂"
                font.pixelSize: 13
                Accessible.name: qsTr("Previous month")
                onClicked: calendar.month = new Date(calendar.month.getFullYear(), calendar.month.getMonth() - 1, 1)
            }
            Label { Layout.fillWidth: true; text: Qt.formatDate(calendar.month, "MMMM, yyyy") }
            Controls.ToolButton {
                text: "▸"
                font.pixelSize: 13
                Accessible.name: qsTr("Next month")
                onClicked: calendar.month = new Date(calendar.month.getFullYear(), calendar.month.getMonth() + 1, 1)
            }
        }
        Controls.DayOfWeekRow {
            Layout.fillWidth: true
            Layout.preferredHeight: 16
            font.family: "Segoe UI"
            font.pixelSize: 12
        }
        Controls.MonthGrid {
            Layout.fillWidth: true
            Layout.fillHeight: true
            month: calendar.month.getMonth()
            year: calendar.month.getFullYear()
            font.family: "Segoe UI"
            font.pixelSize: 12
            palette.windowText: "#152539"
        }
    }
    Rectangle {
        id: dial
        anchors.right: parent.right
        anchors.rightMargin: 18
        y: 44
        width: 124
        height: width
        radius: width / 2
        border.color: "#949ba5"
        gradient: Gradient {
            GradientStop { position: 0; color: "#f9faff" }
            GradientStop { position: 0.51; color: "#c0c6cd" }
            GradientStop { position: 1; color: "#9da6b0" }
        }
        Rectangle {
            anchors.fill: parent
            anchors.margins: 4
            radius: width / 2
            border.color: "#a8b2ba"
            gradient: Gradient {
                GradientStop { position: 0; color: "#dce3e6" }
                GradientStop { position: 0.54; color: "#f1f5f6" }
                GradientStop { position: 0.55; color: "#d3dcdf" }
                GradientStop { position: 1; color: "#f5f8f9" }
            }
        }
        Repeater {
            model: 60
            Item {
                required property int index
                anchors.fill: parent
                rotation: index * 6
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    y: 8
                    width: index % 5 ? 1 : 2
                    height: index % 5 ? 2 : 6
                    color: index % 5 ? "#91a0a7" : "#637b86"
                }
            }
        }
        Repeater {
            model: [calendar.now.getHours() * 30 + calendar.now.getMinutes() / 2,
                    calendar.now.getMinutes() * 6, calendar.now.getSeconds() * 6]
            Item {
                required property real modelData
                required property int index
                anchors.fill: parent
                rotation: modelData
                Rectangle {
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.bottom: parent.verticalCenter
                    width: index === 2 ? 1 : 2
                    height: index === 0 ? 34 : 47
                    color: index === 2 ? "#647a83" : "#344950"
                }
            }
        }
        Rectangle { anchors.centerIn: parent; width: 5; height: 5; radius: 3; color: "#27434c" }
    }
    Label {
        anchors.horizontalCenter: dial.horizontalCenter
        anchors.top: dial.bottom
        anchors.topMargin: 6
        text: Qt.formatTime(calendar.now, Qt.locale().timeFormat(Locale.LongFormat).replace(/\s*t+\s*$/, ""))
    }
    Rectangle {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: 43
        gradient: Gradient {
            GradientStop { position: 0; color: "#ccd9ea" }
            GradientStop { position: 0.13; color: "#f1f5fb" }
            GradientStop { position: 1; color: "#f1f5fb" }
        }
        Controls.ToolButton {
            anchors.centerIn: parent
            text: qsTr("Change date and time settings…")
            contentItem: Label {
                text: parent.text
                color: "#0066cc"
                font.underline: parent.hovered || parent.activeFocus
            }
            background: Item {}
            onClicked: calendar.settingsRequested()
        }
    }
}
