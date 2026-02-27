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
        anchors.fill: parent   // ApplicationWindow sizes content area between header/footer automatically
        currentIndex: tabBar.currentIndex

        DashboardView    { id: dashView }
        ProfileEditorView {
            id: editorView
            // Handle "load profile → switch to editor" from Library
        }
        LibraryView {
            id: libraryView
            onNavRequest: function(idx) { tabBar.currentIndex = idx }
        }
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
        }

        // Action bar — always visible
        Rectangle {
            width: parent.width
            height: 60
            color: "#121212"

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
                    onClicked: controller.toggleProfile()
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
            }
        }
    }
}
