import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

// Scheduled reminders / commands ("yarın 9'da YouTube Music'i aç", "10 dk sonra çayı hatırlat").
HolographicPanel {
    id: root
    title: "Zamanlanmış görevler"
    tag: backend.schedules.filter(s => s.enabled).length + " aktif"
    property real nowMs: Date.now()
    Timer { interval: 20000; running: root.visible; repeat: true; onTriggered: root.nowMs = Date.now() }

    function repeatLabel(r) {
        return { "daily": "her gün", "weekdays": "hafta içi", "weekly": "her hafta", "hourly": "her saat" }[r] || "tek sefer"
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 8
        Text {
            visible: backend.schedules.length === 0
            Layout.fillWidth: true; wrapMode: Text.WordWrap
            text: "Henüz zamanlanmış görev yok. Örnek: “Volb, yarın saat 9'da YouTube Music'i aç”, “10 dakika sonra bana çayı hatırlat”, “her gün 08:30'da yapay zekâ haberlerini araştır”."
            color: Theme.muted; font.family: Theme.font; font.pixelSize: 12
        }
        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 6
            model: backend.schedules
            ScrollBar.vertical: ScrollBar { width: 6 }
            delegate: Rectangle {
                width: list.width - 8
                height: 54
                radius: 8
                opacity: modelData.enabled ? 1 : 0.5
                color: Qt.rgba(0.03, 0.07, 0.12, 0.9)
                border.color: modelData.enabled ? Theme.alpha(modelData.kind === "reminder" ? Theme.amber : Theme.cyan, 0.45) : Theme.border
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 10
                    spacing: 12
                    Text { text: modelData.kind === "reminder" ? "⏰" : "▶"; font.pixelSize: 18
                           color: modelData.kind === "reminder" ? Theme.amber : Theme.cyan }
                    Column {
                        Layout.fillWidth: true
                        Text { text: modelData.payload; color: Theme.text; font.family: Theme.font; font.pixelSize: 14; elide: Text.ElideRight; width: parent.width }
                        Text {
                            width: parent.width; elide: Text.ElideRight
                            text: root.repeatLabel(modelData.repeat)
                                  + (modelData.lastRun ? "  •  son: " + modelData.lastRun + " " + modelData.last_result : (modelData.last_result ? "  •  " + modelData.last_result : ""))
                            color: Theme.dim; font.family: Theme.font; font.pixelSize: 11
                        }
                    }
                    Column {
                        Text { anchors.right: parent.right; text: modelData.enabled ? modelData.when : "bitti/kapalı"; color: Theme.text; font.family: Theme.mono; font.pixelSize: 13 }
                        Text { anchors.right: parent.right; visible: !!modelData.enabled
                               text: Theme.countdown(modelData.run_at, root.nowMs) + " sonra"; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 10 }
                    }
                    HudSwitch { checked: !!modelData.enabled; implicitWidth: 38; implicitHeight: 20; onToggled: (v) => backend.setScheduleEnabled(modelData.id, v) }
                    HudButton { icon: "▶"; implicitWidth: 32; implicitHeight: 28; onClicked: backend.runScheduleNow(modelData.id) }
                    HudButton { icon: "🗑"; danger: true; implicitWidth: 32; implicitHeight: 28; onClicked: backend.deleteSchedule(modelData.id) }
                }
            }
        }
    }
}
