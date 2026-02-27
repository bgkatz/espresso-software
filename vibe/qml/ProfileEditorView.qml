// ProfileEditorView.qml — touch-friendly profile step editor
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts

Item {
    id: root

    // -----------------------------------------------------------------------
    // Step list
    // -----------------------------------------------------------------------
    ListView {
        id: stepList
        anchors {
            top:    parent.top
            left:   parent.left
            right:  parent.right
            bottom: actionBar.top
        }
        anchors.margins: 10
        anchors.bottomMargin: 6
        spacing: 6
        clip: true
        model: profileModel

        header: Rectangle {
            width: stepList.width
            height: 32
            color: "#1e1e1e"
            Row {
                anchors.fill: parent
                anchors.leftMargin: 52
                spacing: 0
                Repeater {
                    model: ["MODE", "SET", "Tw °C", "Tg °C", "EXIT WHEN", "EXIT AT"]
                    Text {
                        width: (stepList.width - 52) / 6
                        text: modelData
                        color: "#666"
                        font.pixelSize: 11
                        font.letterSpacing: 1.0
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                        height: 32
                    }
                }
            }
        }

        delegate: Item {
            id: delegateRoot
            width: stepList.width
            height: 60

            // ---- Background card ----
            Rectangle {
                id: card
                anchors.fill: parent
                radius: 8
                color:  isActive ? "#1a3a2a" : "#252526"
                border.color: isActive ? "#2ecc71" : "#3e3e42"
                border.width: 1
                property bool isActive: controller.profileRunning && controller.stepIndex === index

                // Active-step left accent bar
                Rectangle {
                    visible: card.isActive
                    width: 4; height: parent.height * 0.6; radius: 2; color: "#2ecc71"
                    anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
                }

                // Step content row
                Row {
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.rightMargin: 8

                    Text {                              // index number
                        width: 32; height: parent.height
                        text: index + 1
                        color: "#555"; font.pixelSize: 12
                        verticalAlignment: Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                    }

                    // The 6 data columns — values come from model roles in this delegate's scope
                    Repeater {
                        model: [stepMode,
                                setVal.toFixed(1),
                                tw.toFixed(0),
                                tg.toFixed(0),
                                exitCond,
                                exitVal.toFixed(1)]
                        Text {
                            width: (delegateRoot.width - 52) / 6
                            height: delegateRoot.height
                            text: modelData
                            color: "white"; font.pixelSize: 14
                            verticalAlignment:   Text.AlignVCenter
                            horizontalAlignment: Text.AlignHCenter
                        }
                    }
                }
            }

            // ---- Delete reveal panel (swipe-left target) ----
            Rectangle {
                id: deletePanel
                anchors { right: card.right; top: card.top; bottom: card.bottom }
                width: 0
                radius: 8; color: "#c0392b"; clip: true
                Text {
                    anchors.centerIn: parent
                    text: "DELETE"; color: "white"; font.pixelSize: 12; font.bold: true
                    visible: deletePanel.width > 50
                }
            }

            // ---- Single MouseArea handles both tap and swipe ----
            MouseArea {
                anchors.fill: parent
                property real pressX: 0
                property bool dragging: false

                onPressed: function(mouse) {
                    pressX   = mouse.x
                    dragging = false
                }

                onPositionChanged: function(mouse) {
                    var delta = pressX - mouse.x
                    if (delta > 8) dragging = true
                    deletePanel.width = Math.max(0, Math.min(110, delta))
                }

                onReleased: function(mouse) {
                    var delta = pressX - mouse.x
                    if (delta > 80) {
                        controller.profileModel.removeStep(index)
                    } else if (!dragging) {
                        // Pass values directly from the delegate's model roles
                        editDialog.openForStep(index, stepMode, setVal, tw, tg, exitCond, exitVal)
                    } else {
                        deletePanel.width = 0
                    }
                }
            }
        }
    }

    // -----------------------------------------------------------------------
    // Bottom action bar
    // -----------------------------------------------------------------------
    RowLayout {
        id: actionBar
        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
        anchors.margins: 10
        height: 52
        spacing: 8

        Button {
            Layout.fillWidth: true
            text: "+ ADD STEP"
            Material.background: "#3e3e42"
            onClicked: controller.profileModel.addStep()
        }

        Button {
            Layout.fillWidth: true
            text: "SAVE PROFILE"
            Material.background: "#007acc"
            onClicked: saveDialog.open()
        }
    }

    // -----------------------------------------------------------------------
    // Step edit dialog — receives values directly from the delegate
    // -----------------------------------------------------------------------
    Dialog {
        id: editDialog

        property int    editRow:      -1
        property string editMode:     "P"
        property real   editSetVal:   0.0
        property real   editTw:       93.0
        property real   editTg:       93.0
        property string editExitCond: "Time >"
        property real   editExitVal:  5.0

        function openForStep(row, mode, setVal, tw, tg, exitCond, exitVal) {
            editRow      = row
            editMode     = mode
            editSetVal   = setVal
            editTw       = tw
            editTg       = tg
            editExitCond = exitCond
            editExitVal  = exitVal
            open()
        }

        anchors.centerIn: Overlay.overlay
        width:  Math.min(parent.width * 0.88, 580)
        modal:  true
        title:  editRow >= 0 ? "Edit Step " + (editRow + 1) : ""
        Material.theme: Material.Dark

        onAccepted: {
            if (editRow < 0) return
            var m = profileModel
            m.setMode(editRow,     editMode)
            m.setSetVal(editRow,   editSetVal)
            m.setTw(editRow,       editTw)
            m.setTg(editRow,       editTg)
            m.setExitCond(editRow, editExitCond)
            m.setExitVal(editRow,  editExitVal)
        }

        standardButtons: Dialog.Ok | Dialog.Cancel

        ColumnLayout {
            width: parent.width
            spacing: 18

            // ---- Mode selector ----
            RowLayout {
                Layout.fillWidth: true
                Text { text: "Mode"; color: "#aaa"; font.pixelSize: 14; Layout.preferredWidth: 115 }
                Row {
                    spacing: 8
                    Repeater {
                        model: ["P", "F"]
                        Button {
                            text: modelData; width: 72; height: 44
                            Material.background: editDialog.editMode === modelData ? "#2ecc71" : "#3e3e42"
                            Material.foreground: editDialog.editMode === modelData ? "black"   : "white"
                            font.bold: true
                            onClicked: editDialog.editMode = modelData
                        }
                    }
                }
                Text {
                    color: "#666"; font.pixelSize: 12
                    text: editDialog.editMode === "P" ? "(pressure control)" : "(flow control)"
                    leftPadding: 8
                }
            }

            // ---- Set value ----
            ColumnLayout {
                Layout.fillWidth: true; spacing: 2
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Set Value"; color: "#aaa"; font.pixelSize: 14; Layout.preferredWidth: 115 }
                    Text {
                        text: editDialog.editSetVal.toFixed(1) + (editDialog.editMode === "P" ? " bar" : " ml/s")
                        color: "#2ecc71"; font.pixelSize: 15; font.bold: true
                    }
                }
                Slider {
                    Layout.fillWidth: true
                    from: 0; to: editDialog.editMode === "P" ? 15 : 8; stepSize: 0.1
                    value: editDialog.editSetVal
                    onMoved: editDialog.editSetVal = Math.round(value * 10) / 10
                    Material.accent: "#2ecc71"
                }
            }

            // ---- Water temperature ----
            ColumnLayout {
                Layout.fillWidth: true; spacing: 2
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Water Temp"; color: "#aaa"; font.pixelSize: 14; Layout.preferredWidth: 115 }
                    Text { text: editDialog.editTw.toFixed(1) + " °C"; color: "#e74c3c"; font.pixelSize: 15; font.bold: true }
                }
                Slider {
                    Layout.fillWidth: true
                    from: 80; to: 105; stepSize: 0.5
                    value: editDialog.editTw
                    onMoved: editDialog.editTw = Math.round(value * 2) / 2
                    Material.accent: "#e74c3c"
                }
            }

            // ---- Group temperature ----
            ColumnLayout {
                Layout.fillWidth: true; spacing: 2
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Group Temp"; color: "#aaa"; font.pixelSize: 14; Layout.preferredWidth: 115 }
                    Text { text: editDialog.editTg.toFixed(1) + " °C"; color: "#f39c12"; font.pixelSize: 15; font.bold: true }
                }
                Slider {
                    Layout.fillWidth: true
                    from: 80; to: 105; stepSize: 0.5
                    value: editDialog.editTg
                    onMoved: editDialog.editTg = Math.round(value * 2) / 2
                    Material.accent: "#f39c12"
                }
            }

            // ---- Exit condition ----
            RowLayout {
                Layout.fillWidth: true
                Text { text: "Exit When"; color: "#aaa"; font.pixelSize: 14; Layout.preferredWidth: 115 }
                ComboBox {
                    model: ["Time >", "Weight >", "Press >", "Press <"]
                    currentIndex: {
                        var idx = model.indexOf(editDialog.editExitCond)
                        return idx >= 0 ? idx : 0
                    }
                    onActivated: editDialog.editExitCond = currentText
                    implicitWidth: 160
                    Material.background: "#3e3e42"
                    contentItem: Text {
                        text: parent.displayText; color: "white"
                        font.pixelSize: 13; leftPadding: 8
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }

            // ---- Exit value ----
            ColumnLayout {
                Layout.fillWidth: true; spacing: 2
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Exit Value"; color: "#aaa"; font.pixelSize: 14; Layout.preferredWidth: 115 }
                    Text {
                        text: {
                            var v = editDialog.editExitVal.toFixed(1)
                            var c = editDialog.editExitCond
                            if (c === "Time >")   return v + " s"
                            if (c === "Weight >") return v + " g"
                            return v + " bar"
                        }
                        color: "white"; font.pixelSize: 15; font.bold: true
                    }
                }
                Slider {
                    Layout.fillWidth: true
                    from: 0
                    to: editDialog.editExitCond === "Time >" ? 120
                      : editDialog.editExitCond === "Weight >" ? 80 : 15
                    stepSize: 0.1
                    value: editDialog.editExitVal
                    onMoved: editDialog.editExitVal = Math.round(value * 10) / 10
                }
            }
        }
    }

    // -----------------------------------------------------------------------
    // Save profile dialog
    // -----------------------------------------------------------------------
    Dialog {
        id: saveDialog
        anchors.centerIn: Overlay.overlay
        width: 400
        title: "Save Profile"
        modal: true
        Material.theme: Material.Dark
        standardButtons: Dialog.Ok | Dialog.Cancel

        onOpened:   nameField.forceActiveFocus()
        onAccepted: {
            var n = nameField.text.trim()
            if (n !== "") controller.saveProfile(n)
            nameField.text = ""
        }
        onRejected: nameField.text = ""

        Column {
            width: parent.width
            spacing: 12
            Text { text: "Profile name:"; color: "#aaa"; font.pixelSize: 14 }
            TextField {
                id: nameField
                width: parent.width
                placeholderText: "e.g. Classic 9-Bar"
                color: "white"
                font.pixelSize: 14
                Material.accent: "#2ecc71"
                Keys.onReturnPressed: saveDialog.accept()
            }
        }
    }
}
