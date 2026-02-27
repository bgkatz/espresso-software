// PressureGauge.qml — animated arc gauge for pressure
import QtQuick

Canvas {
    id: root

    property real value:    0.0     // bound to controller.pressure
    property real minValue: 0.0
    property real maxValue: 15.0
    property string label:  "PRESSURE"

    // Smoothly animated display value
    property real _display: 0.0

    Behavior on _display {
        NumberAnimation { duration: 250; easing.type: Easing.OutQuad }
    }

    onValueChanged:    { _display = value }
    on_DisplayChanged: { requestPaint() }

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()

        var cx = width  / 2
        var cy = height * 0.54
        var r  = Math.min(width * 0.44, height * 0.46)

        // Arc runs from 225° (bottom-left) to 315° (bottom-right) — 270° sweep
        var startRad = Math.PI * 1.25    // 225°
        var sweepRad = Math.PI * 1.5     // 270°
        var endRad   = startRad + sweepRad

        var fraction = Math.max(0, Math.min(1,
            (_display - minValue) / (maxValue - minValue)))

        // --- Track (background arc) ---
        ctx.beginPath()
        ctx.arc(cx, cy, r, startRad, endRad)
        ctx.strokeStyle = "#333333"
        ctx.lineWidth   = 14
        ctx.lineCap     = "butt"
        ctx.stroke()

        // --- Value arc ---
        if (fraction > 0.001) {
            // Colour shifts green → amber → red as pressure rises
            var hue = (1.0 - fraction) * 120   // 120=green, 0=red
            ctx.beginPath()
            ctx.arc(cx, cy, r, startRad, startRad + fraction * sweepRad)
            ctx.strokeStyle = Qt.hsla(hue / 360, 0.85, 0.52, 1.0)
            ctx.lineWidth   = 14
            ctx.lineCap     = "round"
            ctx.stroke()
        }

        // --- Tick marks at 0, 3, 6, 9, 12, 15 bar ---
        ctx.strokeStyle = "#555555"
        ctx.lineWidth   = 2
        for (var bar = 0; bar <= maxValue; bar += 3) {
            var frac  = (bar - minValue) / (maxValue - minValue)
            var angle = startRad + frac * sweepRad
            var x1 = cx + Math.cos(angle) * (r - 18)
            var y1 = cy + Math.sin(angle) * (r - 18)
            var x2 = cx + Math.cos(angle) * (r - 6)
            var y2 = cy + Math.sin(angle) * (r - 6)
            ctx.beginPath()
            ctx.moveTo(x1, y1)
            ctx.lineTo(x2, y2)
            ctx.stroke()
        }

        // --- Centre value text ---
        ctx.textAlign    = "center"
        ctx.textBaseline = "middle"
        ctx.fillStyle    = "white"
        ctx.font         = `bold ${Math.round(height * 0.20)}px 'Segoe UI'`
        ctx.fillText(_display.toFixed(1), cx, cy - r * 0.05)

        // --- Unit label below value ---
        ctx.fillStyle = "#aaaaaa"
        ctx.font      = `${Math.round(height * 0.09)}px 'Segoe UI'`
        ctx.fillText("bar", cx, cy + r * 0.22)

        // --- Card label at very bottom ---
        ctx.fillStyle = "#666666"
        ctx.font      = `${Math.round(height * 0.075)}px 'Segoe UI'`
        ctx.fillText(label, cx, cy + r * 0.55)
    }
}
