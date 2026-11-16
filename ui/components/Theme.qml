pragma Singleton
import QtQuick

QtObject {
    readonly property color bg: "#05080E"
    readonly property color panel: "#0B1420"
    readonly property color panelGlass: Qt.rgba(0.043, 0.078, 0.125, 0.80)
    readonly property color panelHi: "#112033"
    readonly property color cyan: "#00D9FF"
    readonly property color blue: "#176BFF"
    readonly property color text: "#EAF6FF"
    readonly property color muted: "#7890A8"
    readonly property color dim: "#3A4C60"
    readonly property color red: "#FF3B5C"
    readonly property color amber: "#FFB020"
    readonly property color green: "#2BE38B"
    readonly property color border: Qt.rgba(0, 0.85, 1, 0.22)
    readonly property color borderStrong: Qt.rgba(0, 0.85, 1, 0.5)

    readonly property string font: "Fira Sans"
    readonly property string mono: "Noto Sans Mono"

    function alpha(c, a) { return Qt.rgba(c.r, c.g, c.b, a) }

    function stateColor(s) {
        switch (s) {
        case "listening": return cyan
        case "thinking": return blue
        case "speaking": return "#5CF2FF"
        case "working": return amber
        case "error": return red
        default: return cyan
        }
    }
    function stateLabel(s) {
        switch (s) {
        case "listening": return "DİNLİYOR"
        case "thinking": return "DÜŞÜNÜYOR"
        case "speaking": return "KONUŞUYOR"
        case "working": return "ÇALIŞIYOR"
        case "error": return "HATA"
        default: return "BEKLEMEDE"
        }
    }
    function taskColor(s) {
        switch (s) {
        case "completed": return green
        case "failed": return red
        case "cancelled": return muted
        case "waiting_approval": return amber
        case "running": return cyan
        case "planning": return blue
        default: return muted
        }
    }

    function fmtTokens(n) {
        n = Number(n || 0)
        if (n >= 1e6) return (n / 1e6).toFixed(n >= 1e7 ? 1 : 2).replace(".", ",") + " mn"
        if (n >= 1e3) return (n / 1e3).toFixed(n >= 1e5 ? 0 : 1).replace(".", ",") + " bin"
        return String(n)
    }
    function fmtUsd(v) { v = Number(v || 0); return "$" + v.toFixed(v < 1 ? 3 : 2) }
    function limitLabel(t) {
        switch (t) {
        case "five_hour": return "5 saatlik oturum"
        case "seven_day": return "Haftalık"
        case "seven_day_opus": return "Haftalık (Opus)"
        case "seven_day_sonnet": return "Haftalık (Sonnet)"
        default: return t || "Limit"
        }
    }
    function limitStatus(s) {
        switch (s) {
        case "allowed": return "Normal"
        case "allowed_warning": return "Limite yaklaşıyorsun"
        case "rejected": return "Limit doldu"
        default: return s || "bilinmiyor"
        }
    }
    function limitColor(s) { return s === "rejected" ? red : s === "allowed_warning" ? amber : green }
    function countdown(epochSec, nowMs) {
        if (!epochSec) return "—"
        let d = Math.max(0, Math.round(epochSec - nowMs / 1000))
        const days = Math.floor(d / 86400); d -= days * 86400
        const h = Math.floor(d / 3600); d -= h * 3600
        const m = Math.floor(d / 60)
        return (days ? days + " g " : "") + (h || days ? h + " sa " : "") + m + " dk"
    }
}
