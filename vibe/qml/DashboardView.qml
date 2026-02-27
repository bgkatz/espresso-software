// DashboardView.qml — live gauges + extraction & temperature charts
import QtQuick
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
        height: 170
        spacing: 10

        // Pressure arc gauge
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 200
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

                // Water temp
                Row {
                    spacing: 6
                    anchors.horizontalCenter: parent.horizontalCenter
                    Rectangle { width: 10; height: 10; radius: 5; color: "#e74c3c"; anchors.verticalCenter: parent.verticalCenter }
                    Text {
                        text: controller.tempWater.toFixed(1) + "°"
                        font.pixelSize: 26; font.bold: true; color: "white"
                    }
                }
                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: "WATER"; font.pixelSize: 10; color: "#888"; font.letterSpacing: 1.2
                    font.capitalization: Font.AllUppercase
                }

                Rectangle { width: 80; height: 1; color: "#3e3e42"; anchors.horizontalCenter: parent.horizontalCenter }

                // Group temp
                Row {
                    spacing: 6
                    anchors.horizontalCenter: parent.horizontalCenter
                    Rectangle { width: 10; height: 10; radius: 5; color: "#f39c12"; anchors.verticalCenter: parent.verticalCenter }
                    Text {
                        text: controller.tempGroup.toFixed(1) + "°"
                        font.pixelSize: 26; font.bold: true; color: "white"
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
    // Charts
    // -----------------------------------------------------------------------
    ColumnLayout {
        anchors {
            top:    statsRow.bottom
            bottom: parent.bottom
            left:   parent.left
            right:  parent.right
        }
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

            // Time axis (shared)
            ValueAxis {
                id: axisX
                min: 0; max: 30
                labelFormat:  "%.0fs"
                labelsColor:  "#666"
                gridLineColor:"#2a2a2a"
                color:        "#3e3e42"
                labelsFont.pixelSize: 10
                titleVisible: false
            }

            // Left Y: pressure + flow (0–15 covers both at normal espresso values)
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

            // Right Y: weight (0–60 g)
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

        // --- Temperature chart: Water temp, Group temp ---
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
                min: 0; max: 30
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

    Connections {
        target: controller

        function onSessionStarted() {
            // Clear all series and reset axes to t=0
            pressureSeries.clear()
            flowSeries.clear()
            weightSeries.clear()
            twSeries.clear()
            tgSeries.clear()
            axisX.min  = 0;  axisX.max  = 5
            axisTX.min = 0;  axisTX.max = 5
            axisYWeight.max = 60
            axisTY.max = 100
            chartActive = true
        }

        // Freeze chart when profile or flush ends
        function onProfileRunningChanged() {
            if (!controller.profileRunning) chartActive = false
        }
        function onFlushOnChanged() {
            if (!controller.flushOn) chartActive = false
        }

        function onNewDataPoint(t, p, f, w, tw, tg) {
            if (!chartActive) return

            pressureSeries.append(t, p)
            flowSeries.append(t, f)
            weightSeries.append(t, w)
            twSeries.append(t, tw)
            tgSeries.append(t, tg)

            // Track current time exactly — axis grows smoothly with every point
            var xMax = Math.max(5, t)
            axisX.max  = xMax
            axisTX.max = xMax

            // Expand weight Y if needed
            if (w > axisYWeight.max * 0.85)
                axisYWeight.max = Math.ceil(w / 10) * 10 + 10

            // Expand temp Y if steam pushes it high
            if (tw > axisTY.max * 0.9)
                axisTY.max = Math.ceil(tw / 20) * 20 + 10
        }
    }
}
