// HistoryView.qml — two-panel shot history browser
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtCharts

Item {
    id: root

    property int selectedIndex: -1

    // -----------------------------------------------------------------------
    // Left panel — shot list
    // -----------------------------------------------------------------------
    Rectangle {
        id: leftPanel
        anchors { top: parent.top; left: parent.left; bottom: parent.bottom }
        width: 300
        color: "#1a1a1a"
        border.color: "#3e3e42"
        border.width: 1

        Column {
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: 36

            Rectangle {
                width: parent.width; height: 36
                color: "#121212"
                Text {
                    anchors.centerIn: parent
                    text: "Shot History"
                    color: "#aaa"; font.pixelSize: 13; font.bold: true
                    font.letterSpacing: 1.0
                }
            }
        }

        ListView {
            id: histList
            anchors { top: parent.top; topMargin: 36; left: parent.left; right: parent.right; bottom: parent.bottom }
            clip: true
            model: controller.shotHistory
            spacing: 2

            delegate: Rectangle {
                width: histList.width
                height: 80
                color: root.selectedIndex === index ? "#1a3a2a" : (listArea.containsMouse ? "#252526" : "#1e1e1e")
                border.color: root.selectedIndex === index ? "#2ecc71" : "transparent"
                border.width: 1

                // Green left accent
                Rectangle {
                    visible: root.selectedIndex === index
                    width: 3; height: parent.height * 0.7; radius: 1; color: "#2ecc71"
                    anchors { left: parent.left; verticalCenter: parent.verticalCenter }
                }

                Column {
                    anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter }
                    anchors.leftMargin: 12
                    spacing: 3

                    Text {
                        text: modelData.timestamp_display
                        color: "white"; font.pixelSize: 13; font.bold: true
                    }
                    Text {
                        text: modelData.dose_g.toFixed(1) + "g in → " +
                              modelData.yield_g.toFixed(1) + "g out  " +
                              "1:" + modelData.ratio.toFixed(1) + "  " +
                              modelData.duration_s.toFixed(0) + "s"
                        color: "#888"; font.pixelSize: 11
                    }
                    // Star rating dots
                    Row {
                        spacing: 3
                        Repeater {
                            model: 10
                            Rectangle {
                                width: 7; height: 7; radius: 3
                                color: index < modelData.rating ? "#f39c12" : "#3e3e42"
                            }
                        }
                    }
                }

                MouseArea {
                    id: listArea
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        root.selectedIndex = index
                        controller.loadShotLog(modelData.filename)
                        // Pre-fill notes editor
                        histRatingSlider.value = modelData.rating
                        histNotesArea.text     = modelData.notes
                    }
                }
            }
        }
    }

    // -----------------------------------------------------------------------
    // Right panel — detail view
    // -----------------------------------------------------------------------
    Item {
        id: rightPanel
        anchors { top: parent.top; left: leftPanel.right; right: parent.right; bottom: parent.bottom }
        anchors.leftMargin: 1
        visible: root.selectedIndex >= 0

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 6

            // Stats row
            RowLayout {
                Layout.fillWidth: true
                height: 56
                spacing: 8

                Repeater {
                    model: root.selectedIndex >= 0 && controller.shotHistory.length > root.selectedIndex
                           ? [
                               { label: "DOSE",     val: controller.shotHistory[root.selectedIndex].dose_g.toFixed(1) + " g" },
                               { label: "YIELD",    val: controller.shotHistory[root.selectedIndex].yield_g.toFixed(1) + " g" },
                               { label: "RATIO",    val: "1:" + controller.shotHistory[root.selectedIndex].ratio.toFixed(1) },
                               { label: "DURATION", val: controller.shotHistory[root.selectedIndex].duration_s.toFixed(0) + " s" },
                             ]
                           : []

                    Rectangle {
                        Layout.fillWidth: true
                        height: 56
                        color: "#252526"; radius: 8
                        border.color: "#3e3e42"; border.width: 1
                        Column {
                            anchors.centerIn: parent
                            spacing: 2
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.val; color: "white"; font.pixelSize: 18; font.bold: true }
                            Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.label; color: "#888"; font.pixelSize: 10; font.letterSpacing: 1.2 }
                        }
                    }
                }
            }

            // Extraction chart
            ChartView {
                id: histExtractionChart
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredHeight: parent.height * 0.35

                backgroundColor:  "#1e1e1e"
                plotAreaColor:    "#1e1e1e"
                animationOptions: ChartView.NoAnimation
                antialiasing:     true
                legend.visible:   true
                legend.color:     "#1e1e1e"
                legend.labelColor:"#aaaaaa"
                legend.font.pixelSize: 11
                margins { left: 0; right: 0; top: 4; bottom: 0 }

                ValueAxis { id: hAxisX;  min: 0; max: 60; labelFormat: "%.0fs";  labelsColor: "#666"; gridLineColor: "#2a2a2a"; color: "#3e3e42"; labelsFont.pixelSize: 10; titleVisible: false }
                ValueAxis { id: hAxisYL; min: 0; max: 15; labelFormat: "%.0f";   labelsColor: "#666"; gridLineColor: "#2a2a2a"; color: "#3e3e42"; labelsFont.pixelSize: 10; titleVisible: false }
                ValueAxis { id: hAxisYW; min: 0; max: 60; labelFormat: "%.0fg";  labelsColor: "#555"; gridLineColor: "transparent"; color: "#3e3e42"; labelsFont.pixelSize: 10; titleVisible: false }

                LineSeries { id: hPressure; name: "Pressure (bar)"; color: "#2ecc71"; width: 2; axisX: hAxisX; axisY: hAxisYL }
                LineSeries { id: hFlow;     name: "Flow (ml/s)";     color: "#3498db"; width: 2; axisX: hAxisX; axisY: hAxisYL }
                LineSeries { id: hWeight;   name: "Weight (g)";      color: "#cccccc"; width: 1.5; style: Qt.DashLine; axisX: hAxisX; axisYRight: hAxisYW }
            }

            // Temperature chart
            ChartView {
                id: histTempChart
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.preferredHeight: parent.height * 0.22

                backgroundColor:  "#1e1e1e"
                plotAreaColor:    "#1e1e1e"
                animationOptions: ChartView.NoAnimation
                antialiasing:     true
                legend.visible:   true
                legend.color:     "#1e1e1e"
                legend.labelColor:"#aaaaaa"
                legend.font.pixelSize: 11
                margins { left: 0; right: 0; top: 4; bottom: 0 }

                ValueAxis { id: hTAxisX; min: 0; max: 60; labelFormat: "%.0fs";  labelsColor: "#666"; gridLineColor: "#2a2a2a"; color: "#3e3e42"; labelsFont.pixelSize: 10; titleVisible: false }
                ValueAxis { id: hTAxisY; min: 15; max: 100; labelFormat: "%.0f°"; labelsColor: "#666"; gridLineColor: "#2a2a2a"; color: "#3e3e42"; labelsFont.pixelSize: 10; titleVisible: false }

                LineSeries { id: hTw; name: "Water (°C)"; color: "#e74c3c"; width: 2; axisX: hTAxisX; axisY: hTAxisY }
                LineSeries { id: hTg; name: "Group (°C)"; color: "#f39c12"; width: 2; axisX: hTAxisX; axisY: hTAxisY }
            }

            // Notes section
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: notesCol.implicitHeight + 20
                color: "#1e1e1e"; radius: 8
                border.color: "#3e3e42"; border.width: 1

                Column {
                    id: notesCol
                    anchors { left: parent.left; right: parent.right; top: parent.top }
                    anchors.margins: 10
                    spacing: 8

                    // Rating row
                    RowLayout {
                        width: parent.width
                        Text { text: "Rating"; color: "#aaa"; font.pixelSize: 13; Layout.preferredWidth: 70 }
                        Slider {
                            id: histRatingSlider
                            Layout.fillWidth: true
                            from: 0; to: 10; stepSize: 1
                            value: 0
                            Material.accent: "#f39c12"
                        }
                        Text {
                            text: histRatingSlider.value > 0 ? histRatingSlider.value + "/10" : "—"
                            color: "#f39c12"; font.pixelSize: 13; font.bold: true
                            Layout.preferredWidth: 40
                        }
                    }

                    // Notes text
                    TextArea {
                        id: histNotesArea
                        width: parent.width
                        height: 56
                        placeholderText: "Tasting notes..."
                        color: "white"; font.pixelSize: 12
                        wrapMode: TextArea.Wrap
                        leftPadding: 8; rightPadding: 8
                        topPadding: 6; bottomPadding: 6
                        background: Rectangle { color: "#2a2a2a"; radius: 4 }
                    }

                    // Save button
                    Button {
                        text: "Save Notes"
                        Material.background: "#2471a3"
                        font.pixelSize: 12
                        onClicked: {
                            if (root.selectedIndex >= 0 && controller.shotHistory.length > root.selectedIndex) {
                                // Point _last_log_fname at the selected shot's csv so saveShotNotes works
                                var fname = controller.shotHistory[root.selectedIndex].filename
                                // We use a dedicated save approach — update the meta file via Python
                                controller.saveHistoryNotes(fname, Math.round(histRatingSlider.value), histNotesArea.text)
                            }
                        }
                    }
                }
            }
        }
    }

    // -----------------------------------------------------------------------
    // Populate charts when shot log data arrives
    // -----------------------------------------------------------------------
    Connections {
        target: controller

        function onShotLogDataReady() {
            var t  = controller.loadedShotTimes
            var p  = controller.loadedShotPressures
            var f  = controller.loadedShotFlows
            var w  = controller.loadedShotWeights
            var tw = controller.loadedShotTw
            var tg = controller.loadedShotTg

            hPressure.clear(); hFlow.clear(); hWeight.clear()
            hTw.clear();       hTg.clear()

            if (t.length === 0) return

            var maxT = t[t.length - 1]
            hAxisX.max  = Math.max(maxT + 2, 10)
            hTAxisX.max = Math.max(maxT + 2, 10)

            var maxW = 0
            for (var i = 0; i < t.length; i++) {
                hPressure.append(t[i], p[i])
                hFlow.append(t[i], f[i])
                hWeight.append(t[i], w[i])
                hTw.append(t[i], tw[i])
                hTg.append(t[i], tg[i])
                if (w[i] > maxW) maxW = w[i]
            }
            if (maxW > 0)
                hAxisYW.max = Math.ceil(maxW / 10) * 10 + 10
        }
    }
}
