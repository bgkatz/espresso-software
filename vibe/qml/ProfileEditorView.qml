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

        delegate: Rectangle {
            id: delegateRoot
            width: stepList.width
            height: 60
            radius: 8
            color:  isActive ? "#1a3a2a" : "#252526"
            border.color: isActive ? "#2ecc71" : "#3e3e42"
            border.width: 1
            property bool isActive: controller.profileRunning && controller.stepIndex === index

            // Active-step left accent bar
            Rectangle {
                visible: delegateRoot.isActive
                width: 4; height: parent.height * 0.6; radius: 2; color: "#2ecc71"
                anchors { left: parent.left; leftMargin: 8; verticalCenter: parent.verticalCenter }
            }

            // ---- Row: step number | 6 data columns | delete button ----
            Row {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 8

                // Step number
                Text {
                    width: 28; height: parent.height
                    text: index + 1
                    color: "#555"; font.pixelSize: 12
                    verticalAlignment: Text.AlignVCenter
                    horizontalAlignment: Text.AlignHCenter
                }

                // 6 data columns — stretch to fill available space minus delete button
                Repeater {
                    model: [stepMode === "P" ? "Pressure" : "Flow",
                            setVal.toFixed(1),
                            tw.toFixed(0),
                            tg.toFixed(0),
                            exitCond,
                            exitVal.toFixed(1)]
                    Text {
                        width: (delegateRoot.width - 28 - 12 - 8 - 52) / 6
                        height: delegateRoot.height
                        text: modelData
                        color: "white"; font.pixelSize: 14
                        verticalAlignment:   Text.AlignVCenter
                        horizontalAlignment: Text.AlignHCenter
                    }
                }

                // ---- Delete button ----
                Rectangle {
                    width: 44; height: 44
                    anchors.verticalCenter: parent.verticalCenter
                    radius: 6
                    color: deleteArea.pressed ? "#922b21" : "#c0392b"

                    Text {
                        anchors.centerIn: parent
                        text: "✕"
                        color: "white"; font.pixelSize: 16; font.bold: true
                    }

                    MouseArea {
                        id: deleteArea
                        anchors.fill: parent
                        onClicked: profileModel.removeStep(index)
                    }
                }
            }

            // ---- Tap anywhere on the row (except the delete button) to edit ----
            MouseArea {
                anchors { fill: parent; rightMargin: 52 }
                onClicked: editDialog.openForStep(index, stepMode, setVal, tw, tg, exitCond, exitVal, rampTime, flowLimit)
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

        property int    editRow:       -1
        property string editMode:      "P"
        property real   editSetVal:    0.0
        property real   editTw:        93.0
        property real   editTg:        93.0
        property string editExitCond:  "Time >"
        property real   editExitVal:   5.0
        property real   editRampTime:  0.0
        property real   editFlowLimit: 0.0

        function openForStep(row, mode, setVal, tw, tg, exitCond, exitVal, rampTime, flowLimit) {
            editRow       = row
            editMode      = mode
            editSetVal    = setVal
            editTw        = tw
            editTg        = tg
            editExitCond  = exitCond
            editExitVal   = exitVal
            editRampTime  = rampTime
            editFlowLimit = flowLimit !== undefined ? flowLimit : 0.0
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
            m.setMode(editRow,      editMode)
            m.setSetVal(editRow,    editSetVal)
            m.setTw(editRow,        editTw)
            m.setTg(editRow,        editTg)
            m.setExitCond(editRow,  editExitCond)
            m.setExitVal(editRow,   editExitVal)
            m.setRampTime(editRow,  editRampTime)
            m.setFlowLimit(editRow, editFlowLimit)
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
                        model: [{ label: "Pressure", value: "P" },
                                { label: "Flow",     value: "F" }]
                        Button {
                            text: modelData.label; width: 90; height: 44
                            Material.background: editDialog.editMode === modelData.value ? "#2ecc71" : "#3e3e42"
                            Material.foreground: editDialog.editMode === modelData.value ? "black"   : "white"
                            font.bold: true
                            onClicked: editDialog.editMode = modelData.value
                        }
                    }
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

            // ---- Ramp time ----
            ColumnLayout {
                Layout.fillWidth: true; spacing: 2
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Ramp Time"; color: "#aaa"; font.pixelSize: 14; Layout.preferredWidth: 115 }
                    Text {
                        text: editDialog.editRampTime > 0
                              ? editDialog.editRampTime.toFixed(1) + " s"
                              : "Instant"
                        color: "#9b59b6"; font.pixelSize: 15; font.bold: true
                    }
                }
                Slider {
                    Layout.fillWidth: true
                    from: 0; to: 10; stepSize: 0.5
                    value: editDialog.editRampTime
                    onMoved: editDialog.editRampTime = Math.round(value * 2) / 2
                    Material.accent: "#9b59b6"
                }
            }

            // ---- Flow limit (Pressure mode only) ----
            ColumnLayout {
                Layout.fillWidth: true; spacing: 2
                visible: editDialog.editMode === "P"
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Flow Limit"; color: "#aaa"; font.pixelSize: 14; Layout.preferredWidth: 115 }
                    Text {
                        text: editDialog.editFlowLimit > 0
                              ? editDialog.editFlowLimit.toFixed(1) + " ml/s"
                              : "Off"
                        color: "#1abc9c"; font.pixelSize: 15; font.bold: true
                    }
                }
                Slider {
                    Layout.fillWidth: true
                    from: 0; to: 8; stepSize: 0.5
                    value: editDialog.editFlowLimit
                    onMoved: editDialog.editFlowLimit = Math.round(value * 2) / 2
                    Material.accent: "#1abc9c"
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
                    model: ["Time >", "Weight >", "Pressure >", "Pressure <"]
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
