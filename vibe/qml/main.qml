// main.qml — root application window
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts

ApplicationWindow {
    id: appWindow
    title: "PiEspresso"
    width:  1280
    height: 800
    visible: true

    Material.theme:  Material.Dark
    Material.accent: Material.Green

    // -----------------------------------------------------------------------
    // Header toolbar
    // -----------------------------------------------------------------------
    header: ToolBar {
        height: 56
        Material.background: "#121212"

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin:  12
            anchors.rightMargin: 12
            spacing: 12

            // App name / status
            Column {
                spacing: 0
                Text {
                    text: "PiEspresso"
                    color: "white"
                    font.pixelSize: 18
                    font.bold: true
                }
                Text {
                    text: controller.statusText
                    color: controller.profileRunning ? "#2ecc71" : "#888"
                    font.pixelSize: 11
                    font.letterSpacing: 1.2
                }
            }

            // Elapsed time (shown only during a shot)
            Text {
                visible: controller.profileRunning || controller.flushOn
                text: {
                    var t = controller.elapsedTime
                    var m = Math.floor(t / 60)
                    var s = Math.floor(t % 60)
                    var ds = Math.floor((t % 1) * 10)
                    return m > 0
                        ? "%1:%2.%3".arg(m).arg(s.toString().padStart(2,'0')).arg(ds)
                        : "%1.%2s".arg(s).arg(ds)
                }
                color: "#2ecc71"
                font.pixelSize: 22
                font.bold: true
                font.family: "Courier New"
            }

            Item { Layout.fillWidth: true }   // spacer

            // Steam button
            Button {
                text: controller.steamOn ? "STEAM  ●" : "STEAM"
                enabled: controller.powered
                highlighted: controller.steamOn
                Material.background: controller.steamOn ? "#c0392b" : "#3e3e42"
                font.pixelSize: 13
                onClicked: controller.toggleSteam()
            }

            // Power button
            Button {
                id: powerBtn
                text: controller.powered ? "ACTIVE" : "STANDBY"
                highlighted: controller.powered
                Material.background: controller.powered ? "#27ae60" : "#3e3e42"
                font.pixelSize: 13
                font.bold: true
                implicitWidth: 110
                onClicked: controller.togglePower()
            }
        }
    }

    // -----------------------------------------------------------------------
    // Central content — three views driven by tab bar
    // -----------------------------------------------------------------------
    StackLayout {
        id: stack
        anchors.fill: parent
        currentIndex: tabBar.currentIndex

        DashboardView    { id: dashView }
        ProfileEditorView {
            id: editorView
        }
        LibraryView {
            id: libraryView
            onNavRequest: function(idx) { tabBar.currentIndex = idx }
        }
        HistoryView { id: historyView }
    }

    // -----------------------------------------------------------------------
    // Footer — tab bar + action buttons
    // -----------------------------------------------------------------------
    footer: Column {
        width: parent.width
        spacing: 0

        // Navigation tabs
        TabBar {
            id: tabBar
            width: parent.width
            Material.background: "#1a1a1a"

            TabButton {
                text: "  Dashboard  "
                font.pixelSize: 13
                implicitHeight: 44
            }
            TabButton {
                text: "  Profile Editor  "
                font.pixelSize: 13
                implicitHeight: 44
            }
            TabButton {
                text: "  Library  "
                font.pixelSize: 13
                implicitHeight: 44
            }
            TabButton {
                text: "  History  "
                font.pixelSize: 13
                implicitHeight: 44
            }

            onCurrentIndexChanged: {
                if (currentIndex === 3) controller.refreshShotHistory()
            }
        }

        // Action bar — always visible
        Rectangle {
            id: actionBar
            width: parent.width
            height: 60
            color: "#121212"

            property string saveLogText: "SAVE LOG"

            Timer {
                id: savedTimer
                interval: 2000
                onTriggered: actionBar.saveLogText = "SAVE LOG"
            }

            Connections {
                target: controller
                function onShotSaved(fname) {
                    actionBar.saveLogText = fname.startsWith("ERROR")
                                           ? "SAVE FAILED"
                                           : "SAVED ✓"
                    savedTimer.restart()
                }
            }

            RowLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 8

                // RUN PROFILE — big green button
                Button {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    text: controller.profileRunning
                          ? ("⏹  STOP  (" + controller.statusText + ")")
                          : "▶  RUN PROFILE"
                    enabled: controller.powered
                    Material.background: controller.profileRunning ? "#e74c3c" : "#27ae60"
                    Material.foreground: "white"
                    font.pixelSize: 15
                    font.bold: true
                    onClicked: {
                        controller.toggleProfile()
                        if (!controller.profileRunning) tabBar.currentIndex = 0
                    }
                }

                // FLUSH button
                Button {
                    Layout.preferredWidth: 120
                    Layout.fillHeight: true
                    text: controller.flushOn ? "■ FLUSH" : "FLUSH"
                    enabled: controller.powered && !controller.profileRunning
                    Material.background: controller.flushOn ? "#e67e22" : "#3e3e42"
                    font.pixelSize: 13
                    font.bold: true
                    onClicked: controller.flushOn ? controller.stopFlush()
                                                  : controller.startFlush()
                }

                // SAVE LOG button — visible after a shot completes
                Button {
                    visible: controller.shotAvailable
                    Layout.preferredWidth: 130
                    Layout.fillHeight: true
                    text: actionBar.saveLogText
                    Material.background: actionBar.saveLogText === "SAVED ✓"     ? "#1e8449"
                                       : actionBar.saveLogText === "SAVE FAILED" ? "#922b21"
                                       : "#6c3483"
                    Material.foreground: "white"
                    font.pixelSize: 13
                    font.bold: true
                    onClicked: controller.saveShot()
                }

                // NOTES button — visible after a shot is saved (lastLogFname is set)
                Button {
                    visible: controller.shotAvailable
                    Layout.preferredWidth: 100
                    Layout.fillHeight: true
                    text: "NOTES"
                    Material.background: "#2471a3"
                    Material.foreground: "white"
                    font.pixelSize: 13
                    font.bold: true
                    onClicked: {
                        notesDialog.rating = 0
                        notesDialog.notes  = ""
                        notesDialog.open()
                    }
                }
            }
        }
    }

    // -----------------------------------------------------------------------
    // Tasting notes dialog
    // -----------------------------------------------------------------------
    Dialog {
        id: notesDialog
        anchors.centerIn: Overlay.overlay
        width: Math.min(parent.width * 0.85, 480)
        modal: true
        title: "Rate this shot"
        Material.theme: Material.Dark
        standardButtons: Dialog.Ok | Dialog.Cancel

        property int    rating: 0
        property string notes:  ""

        onAccepted: controller.saveShotNotes(rating, notes)

        ColumnLayout {
            width: parent.width
            spacing: 16

            // Rating slider
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 4
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: "Rating"; color: "#aaa"; font.pixelSize: 14; Layout.preferredWidth: 80 }
                    Text {
                        text: notesDialog.rating > 0 ? notesDialog.rating + " / 10" : "—"
                        color: "#f39c12"; font.pixelSize: 15; font.bold: true
                    }
                }
                Slider {
                    Layout.fillWidth: true
                    from: 0; to: 10; stepSize: 1
                    value: notesDialog.rating
                    onMoved: notesDialog.rating = Math.round(value)
                    Material.accent: "#f39c12"
                }
            }

            // Tasting notes text area
            Column {
                Layout.fillWidth: true
                spacing: 4
                Text { text: "Tasting notes"; color: "#aaa"; font.pixelSize: 14 }
                ScrollView {
                    width: parent.width
                    height: 80
                    TextArea {
                        id: notesArea
                        placeholderText: "Tasting notes..."
                        color: "white"
                        font.pixelSize: 13
                        wrapMode: TextArea.Wrap
                        leftPadding: 8; rightPadding: 8
                        topPadding: 6; bottomPadding: 6
                        background: Rectangle { color: "#2a2a2a"; radius: 4 }
                        onTextChanged: notesDialog.notes = text
                    }
                }
            }
        }
    }
}
