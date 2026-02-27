// StatCard.qml — a single live-value display tile
import QtQuick
import QtQuick.Controls.Material

Rectangle {
    id: root

    property string label:     "VALUE"
    property real   value:     0.0
    property string unit:      ""
    property int    decimals:  1
    property color  valueColor: "white"

    // Optional: show a TARE button inside the card
    property bool showTare: false
    signal tareClicked()

    radius: 10
    color:  "#252526"
    border.color: "#3e3e42"
    border.width: 1

    Column {
        anchors.centerIn: parent
        spacing: 2

        Row {
            anchors.horizontalCenter: parent.horizontalCenter
            spacing: 6

            Text {
                id: valueText
                text: root.value.toFixed(root.decimals)
                font.pixelSize: 32
                font.bold: true
                color: root.valueColor
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                text: root.unit
                font.pixelSize: 14
                color: "#aaaaaa"
                anchors.verticalCenter: valueText.bottom
                anchors.verticalCenterOffset: -4
            }
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.label
            font.pixelSize: 11
            color: "#888888"
            font.capitalization: Font.AllUppercase
            font.letterSpacing: 1.2
        }

        // Optional tare button
        Rectangle {
            visible: root.showTare
            anchors.horizontalCenter: parent.horizontalCenter
            width: 64; height: 28
            radius: 4
            color: tareArea.pressed ? "#7d3c98" : "#8e44ad"

            Text {
                anchors.centerIn: parent
                text: "TARE"
                font.pixelSize: 11
                font.bold: true
                color: "white"
            }

            MouseArea {
                id: tareArea
                anchors.fill: parent
                onClicked: root.tareClicked()
            }
        }
    }
}
