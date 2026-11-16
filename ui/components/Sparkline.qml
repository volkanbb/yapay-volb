import QtQuick

// Lightweight history chart (values 0..1).
Canvas {
    id: root
    property var values: []
    property color color: Theme.cyan
    onValuesChanged: requestPaint()
    onWidthChanged: requestPaint()
    renderStrategy: Canvas.Cooperative
    onPaint: {
        const ctx = getContext("2d")
        ctx.reset()
        const n = values.length
        ctx.strokeStyle = Qt.rgba(color.r, color.g, color.b, 0.12)
        ctx.lineWidth = 1
        for (let g = 1; g < 4; g++) {
            ctx.beginPath(); ctx.moveTo(0, height * g / 4); ctx.lineTo(width, height * g / 4); ctx.stroke()
        }
        if (n < 2) return
        const step = width / 59
        const x0 = width - (n - 1) * step
        ctx.beginPath()
        ctx.moveTo(x0, height)
        for (let i = 0; i < n; i++) ctx.lineTo(x0 + i * step, height - values[i] * height)
        ctx.lineTo(x0 + (n - 1) * step, height)
        ctx.closePath()
        const grad = ctx.createLinearGradient(0, 0, 0, height)
        grad.addColorStop(0, Qt.rgba(color.r, color.g, color.b, 0.35))
        grad.addColorStop(1, Qt.rgba(color.r, color.g, color.b, 0.0))
        ctx.fillStyle = grad
        ctx.fill()
        ctx.beginPath()
        for (let j = 0; j < n; j++) {
            const x = x0 + j * step, y = height - values[j] * height
            if (j === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
        }
        ctx.strokeStyle = color
        ctx.lineWidth = 2
        ctx.stroke()
    }
}
