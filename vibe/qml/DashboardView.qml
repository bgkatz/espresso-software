// DashboardView.qml — live gauges + extraction & temperature charts
import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtCharts
import "components"

Item {
    id: root

    // -----------------------------------------------------------------------
    // Top row: pressure gauge + stat cards
    // -----------------------------------------------------------------------
    RowLayout {
        id: statsRow
        anchors { top: parent.top; left: parent.left; right: parent.right }
        anchors.margins: 10
        height: 150
        spacing: 10

        // Pressure arc gauge
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 185
            color:  "#252526"
            radius: 10
            border.color: "#3e3e42"
            border.width: 1

            PressureGauge {
                anchors.fill: parent
                anchors.margins: 8
                value: controller.pressure
                label: "PRESSURE"
            }
        }

        // Flow
        StatCard {
            Layout.fillHeight: true
            Layout.fillWidth: true
            label: "FLOW"
            value: controller.flow
            unit:  "ml/s"
            decimals: 2
            valueColor: "#3498db"
        }

        // Weight + tare
        StatCard {
            Layout.fillHeight: true
            Layout.fillWidth: true
            label:    "WEIGHT"
            value:    controller.weight
            unit:     "g"
            decimals: 1
            showTare: true
            onTareClicked: controller.tare()
        }

        // DOSE card with ▲/▼ buttons
        Rectangle {
            Layout.fillHeight: true
            Layout.fillWidth: true
            color:  "#252526"
            radius: 10
            border.color: "#3e3e42"
            border.width: 1

            Column {
                anchors.centerIn: parent
                spacing: 4

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: controller.dose.toFixed(1) + " g"
                    font.pixelSize: 26; font.bold: true; color: "white"
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "DOSE"; font.pixelSize: 10; color: "#888"
                    font.letterSpacing: 1.2
                    font.capitalization: Font.AllUppercase
                }
                Row {
                    anchors.horizontalCenter: parent.horizontalCenter
                    spacing: 6
                    Rectangle {
                        width: 32; height: 24; radius: 4
                        color: doseDownArea.pressed ? "#1a6b3c" : "#27ae60"
                        Text { anchors.centerIn: parent; text: "▼"; color: "white"; font.pixelSize: 12 }
                        MouseArea {
                            id: doseDownArea
                            anchors.fill: parent
                            onClicked: controller.setDose(controller.dose - 0.5)
                        }
                    }
                    Rectangle {
                        width: 32; height: 24; radius: 4
                        color: doseUpArea.pressed ? "#1a6b3c" : "#27ae60"
                        Text { anchors.centerIn: parent; text: "▲"; color: "white"; font.pixelSize: 12 }
                        MouseArea {
                            id: doseUpArea
                            anchors.fill: parent
                            onClicked: controller.setDose(controller.dose + 0.5)
                        }
                    }
                }
            }
        }

        // RATIO read-only card
        StatCard {
            Layout.fillHeight: true
            Layout.fillWidth: true
            label: "RATIO"
            unit:  ""
            decimals: 1
            value: controller.brewRatio
            valueColor: "#9b59b6"
            // Override the display text via a custom approach — use the label slot
            // We show "1:X.X" format by providing a custom text override
            customText: controller.brewRatio > 0.01
                        ? "1:" + controller.brewRatio.toFixed(1)
                        : "—"
        }

        // Temperatures (custom two-line card)
        Rectangle {
            Layout.fillHeight: true
            Layout.fillWidth: true
            color:  "#252526"
            radius: 10
            border.color: "#3e3e42"
            border.width: 1

            Column {
                anchors.centerIn: parent
                spacing: 6

                Row {
                    spacing: 6
                    anchors.horizontalCenter: parent.horizontalCenter
                    Rectangle { width: 10; height: 10; radius: 5; color: "#e74c3c"; anchors.verticalCenter: parent.verticalCenter }
                    Text {
                        text: controller.tempWater.toFixed(1) + "°"
                        font.pixelSize: 22; font.bold: true; color: "white"
                    }
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "WATER"; font.pixelSize: 10; color: "#888"; font.letterSpacing: 1.2
                    font.capitalization: Font.AllUppercase
                }

                Rectangle { width: 80; height: 1; color: "#3e3e42"; anchors.horizontalCenter: parent.horizontalCenter }

                Row {
                    spacing: 6
                    anchors.horizontalCenter: parent.horizontalCenter
                    Rectangle { width: 10; height: 10; radius: 5; color: "#f39c12"; anchors.verticalCenter: parent.verticalCenter }
                    Text {
                        text: controller.tempGroup.toFixed(1) + "°"
                        font.pixelSize: 22; font.bold: true; color: "white"
                    }
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "GROUP"; font.pixelSize: 10; color: "#888"; font.letterSpacing: 1.2
                    font.capitalization: Font.AllUppercase
                }
            }
        }
    }

    // -----------------------------------------------------------------------
    // Pre-shot ready indicator strip
    // -----------------------------------------------------------------------
    Rectangle {
        id: readyStrip
        anchors { top: statsRow.bottom; left: parent.left; right: parent.right }
        anchors.topMargin: 6
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        height: 28
        color: "#1a1a1a"
        radius: 6

        Row {
            anchors.centerIn: parent
            spacing: 20

            Repeater {
                model: controller.readyState
                Row {
                    spacing: 5
                    anchors.verticalCenter: parent.verticalCenter
                    Rectangle {
                        width: 8; height: 8; radius: 4
                        color: modelData.ok ? "#2ecc71" : "#e74c3c"
                        anchors.verticalCenter: parent.verticalCenter
                    }
                    Text {
                        text: modelData.label + (modelData.detail ? " " + modelData.detail : "")
                        color: modelData.ok ? "#aaa" : "#e74c3c"
                        font.pixelSize: 11
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
            }
        }
    }

    // -----------------------------------------------------------------------
    // Charts
    // -----------------------------------------------------------------------
    ColumnLayout {
        anchors {
            top:    readyStrip.bottom
            bottom: parent.bottom
            left:   parent.left
            right:  parent.right
        }
        anchors.topMargin: 6
        anchors.margins: 10
        spacing: 6

        // --- Extraction chart: Pressure, Flow, Weight ---
        ChartView {
            id: extractionChart
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: parent.height * 0.60

            backgroundColor:  "#1e1e1e"
            plotAreaColor:    "#1e1e1e"
            animationOptions: ChartView.NoAnimation
            antialiasing:     true

            legend.visible:    true
            legend.color:      "#1e1e1e"
            legend.labelColor: "#aaaaaa"
            legend.font.pixelSize: 11

            margins { left: 0; right: 0; top: 4; bottom: 0 }

            ValueAxis {
                id: axisX
                min: 0; max: 5
                labelFormat:  "%.0fs"
                labelsColor:  "#666"
                gridLineColor:"#2a2a2a"
                color:        "#3e3e42"
                labelsFont.pixelSize: 10
                titleVisible: false
            }

            ValueAxis {
                id: axisYLeft
                min: 0; max: 15
                labelFormat:  "%.0f"
                labelsColor:  "#666"
                gridLineColor:"#2a2a2a"
                color:        "#3e3e42"
                labelsFont.pixelSize: 10
                titleVisible: false
            }

            ValueAxis {
                id: axisYWeight
                min: 0; max: 60
                labelFormat:  "%.0fg"
                labelsColor:  "#555"
                gridLineColor:"transparent"
                color:        "#3e3e42"
                labelsFont.pixelSize: 10
                titleVisible: false
            }

            // Ghost series — shot 0 (most recent, opacity 0.40)
            LineSeries {
                id: ghost0P
                name: ""; color: "#2ecc71"; width: 1; opacity: 0.40; style: Qt.DashLine
                axisX: axisX; axisY: axisYLeft
            }
            LineSeries {
                id: ghost0F
                name: ""; color: "#3498db"; width: 1; opacity: 0.40; style: Qt.DashLine
                axisX: axisX; axisY: axisYLeft
            }
            LineSeries {
                id: ghost0W
                name: ""; color: "#888888"; width: 1; opacity: 0.40; style: Qt.DashLine
                axisX: axisX; axisYRight: axisYWeight
            }

            // Ghost series — shot 1 (opacity 0.25)
            LineSeries {
                id: ghost1P
                name: ""; color: "#2ecc71"; width: 1; opacity: 0.25; style: Qt.DashLine
                axisX: axisX; axisY: axisYLeft
            }
            LineSeries {
                id: ghost1F
                name: ""; color: "#3498db"; width: 1; opacity: 0.25; style: Qt.DashLine
                axisX: axisX; axisY: axisYLeft
            }
            LineSeries {
                id: ghost1W
                name: ""; color: "#888888"; width: 1; opacity: 0.25; style: Qt.DashLine
                axisX: axisX; axisYRight: axisYWeight
            }

            // Ghost series — shot 2 (oldest, opacity 0.12)
            LineSeries {
                id: ghost2P
                name: ""; color: "#2ecc71"; width: 1; opacity: 0.12; style: Qt.DashLine
                axisX: axisX; axisY: axisYLeft
            }
            LineSeries {
                id: ghost2F
                name: ""; color: "#3498db"; width: 1; opacity: 0.12; style: Qt.DashLine
                axisX: axisX; axisY: axisYLeft
            }
            LineSeries {
                id: ghost2W
                name: ""; color: "#888888"; width: 1; opacity: 0.12; style: Qt.DashLine
                axisX: axisX; axisYRight: axisYWeight
            }

            // Profile target reference line
            LineSeries {
                id: targetSeries
                name:  ""
                color: "white"; width: 1; opacity: 0.45; style: Qt.DotLine
                axisX: axisX; axisY: axisYLeft
                visible: controller.profileRunning
            }

            LineSeries {
                id: pressureSeries
                name:  "Pressure (bar)"
                color: "#2ecc71"
                width: 2.5
                axisX: axisX
                axisY: axisYLeft
            }

            LineSeries {
                id: flowSeries
                name:  "Flow (ml/s)"
                color: "#3498db"
                width: 2
                axisX: axisX
                axisY: axisYLeft
            }

            LineSeries {
                id: weightSeries
                name:  "Weight (g)"
                color: "#cccccc"
                width: 1.5
                style: Qt.DashLine
                axisX:      axisX
                axisYRight: axisYWeight
            }
        }

        // --- Temperature chart ---
        ChartView {
            id: tempChart
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: parent.height * 0.40

            backgroundColor:  "#1e1e1e"
            plotAreaColor:    "#1e1e1e"
            animationOptions: ChartView.NoAnimation
            antialiasing:     true

            legend.visible:    true
            legend.color:      "#1e1e1e"
            legend.labelColor: "#aaaaaa"
            legend.font.pixelSize: 11

            margins { left: 0; right: 0; top: 4; bottom: 0 }

            ValueAxis {
                id: axisTX
                min: 0; max: 5
                labelFormat:  "%.0fs"
                labelsColor:  "#666"
                gridLineColor:"#2a2a2a"
                color:        "#3e3e42"
                labelsFont.pixelSize: 10
                titleVisible: false
            }

            ValueAxis {
                id: axisTY
                min: 15; max: 100
                labelFormat:  "%.0f°"
                labelsColor:  "#666"
                gridLineColor:"#2a2a2a"
                color:        "#3e3e42"
                labelsFont.pixelSize: 10
                titleVisible: false
            }

            LineSeries {
                id: twSeries
                name:  "Water (°C)"
                color: "#e74c3c"
                width: 2
                axisX: axisTX
                axisY: axisTY
            }

            LineSeries {
                id: tgSeries
                name:  "Group (°C)"
                color: "#f39c12"
                width: 2
                axisX: axisTX
                axisY: axisTY
            }
        }
    }

    // -----------------------------------------------------------------------
    // Chart data connections
    // -----------------------------------------------------------------------
    property bool chartActive: false
    property real xMax: 5
    Behavior on xMax {
        enabled: chartActive
        NumberAnimation { duration: 33; easing.type: Easing.Linear }
    }
    onXMaxChanged: {
        axisX.max  = xMax
        axisTX.max = xMax
        if (controller.profileRunning) updateTargetLine()
    }

    function updateTargetLine() {
        targetSeries.clear()
        if (!controller.profileRunning) return
        var v = controller.currentStepTarget
        targetSeries.append(0, v)
        targetSeries.append(Math.max(xMax + 5, 10), v)
    }

    Connections {
        target: controller

        function onSessionStarted() {
            chartActive = false
            pressureSeries.clear()
            flowSeries.clear()
            weightSeries.clear()
            twSeries.clear()
            tgSeries.clear()
            targetSeries.clear()
            xMax = 5
            axisX.min   = 0
            axisTX.min  = 0
            axisYWeight.max = 60
            axisTY.max  = 100
            chartActive = true
        }

        function onProfileRunningChanged() {
            if (!controller.profileRunning) {
                chartActive = false
                targetSeries.clear()
            }
        }
        function onFlushOnChanged() {
            if (!controller.flushOn) chartActive = false
        }

        function onPreviousShotReady() {
            var history = controller.ghostHistory
            var sets = [
                [ghost0P, ghost0F, ghost0W],
                [ghost1P, ghost1F, ghost1W],
                [ghost2P, ghost2F, ghost2W]
            ]
            for (var i = 0; i < 3; i++) {
                sets[i][0].clear(); sets[i][1].clear(); sets[i][2].clear()
                if (i < history.length) {
                    var entry = history[i]
                    var t = entry.t, p = entry.p, f = entry.f, w = entry.w
                    for (var j = 0; j < t.length; j++) {
                        sets[i][0].append(t[j], p[j])
                        sets[i][1].append(t[j], f[j])
                        sets[i][2].append(t[j], w[j])
                    }
                }
            }
        }

        function onCurrentStepTargetChanged() {
            updateTargetLine()
        }

        function onNewDataPoint(t, p, f, w, tw, tg) {
            if (!chartActive) return

            pressureSeries.append(t, p)
            flowSeries.append(t, f)
            weightSeries.append(t, w)
            twSeries.append(t, tw)
            tgSeries.append(t, tg)

            xMax = Math.max(5, t)

            if (w > axisYWeight.max * 0.85)
                axisYWeight.max = Math.ceil(w / 10) * 10 + 10

            if (tw > axisTY.max * 0.9)
                axisTY.max = Math.ceil(tw / 20) * 20 + 10
        }
    }
}
