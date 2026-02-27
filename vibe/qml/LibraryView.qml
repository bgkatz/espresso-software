// LibraryView.qml — saved profile grid
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts

Item {
    id: root

    // No profiles placeholder
    Text {
        visible: controller.savedProfileNames.length === 0
        anchors.centerIn: parent
        text: "No saved profiles yet.\nGo to Profile Editor → Save Profile."
        color: "#555"
        font.pixelSize: 16
        horizontalAlignment: Text.AlignHCenter
        lineHeight: 1.6
    }

    GridView {
        anchors.fill: parent
        anchors.margins: 12
        cellWidth:  280
        cellHeight: 140
        clip: true
        model: controller.savedProfileNames

        delegate: Rectangle {
            width:  260
            height: 120
            radius: 12
            color:  "#252526"
            border.color: "#3e3e42"
            border.width: 1

            // Hover/press tint
            MouseArea {
                id: cardArea
                anchors.fill: parent
                hoverEnabled: true
            }
            Rectangle {
                anchors.fill: parent
                radius: parent.radius
                color: cardArea.containsPress ? "#ffffff" : "transparent"
                opacity: 0.06
            }

            Column {
                anchors {
                    left:   parent.left;    leftMargin: 16
                    right:  parent.right;   rightMargin: 16
                    top:    parent.top;     topMargin:  16
                }
                spacing: 8

                Text {
                    text: modelData
                    color: "white"
                    font.pixelSize: 16
                    font.bold: true
                    elide: Text.ElideRight
                    width: parent.width
                }

                RowLayout {
                    width: parent.width
                    spacing: 8

                    Button {
                        Layout.fillWidth: true
                        text: "LOAD"
                        height: 38
                        Material.background: "#2ecc71"
                        Material.foreground: "#000"
                        font.bold: true
                        onClicked: {
                            controller.loadProfile(modelData)
                            // Switch to editor tab — signal the parent via a property
                            navRequest(1)
                        }
                    }

                    Button {
                        width: 38; height: 38
                        text: "✕"
                        Material.background: "#c0392b"
                        font.pixelSize: 16
                        onClicked: { deleteConfirm.profileName = modelData; deleteConfirm.open() }
                    }
                }
            }
        }
    }

    // Delete confirmation
    Dialog {
        id: deleteConfirm
        property string profileName: ""
        anchors.centerIn: Overlay.overlay
        title: "Delete Profile"
        modal: true
        Material.theme: Material.Dark
        standardButtons: Dialog.Yes | Dialog.No

        Text {
            text: 'Delete "' + deleteConfirm.profileName + '"?'
            color: "#e0e0e0"
            font.pixelSize: 14
        }

        onAccepted: controller.deleteProfile(profileName)
    }

    // Signal to parent to switch tabs after loading a profile
    signal navRequest(int tabIndex)
}
