import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic

// Right-hand status column: Claude, resources, microphone, active task, recent actions.
Flickable {
    id: root
    contentHeight: col.implicitHeight
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded; width: 6 }

    ColumnLayout {
        id: col
        width: root.width
        spacing: 10

        // Claude ------------------------------------------------------------
        HolographicPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: claudeCol.implicitHeight + 54
            title: "Claude Bağlantısı"
            accent: backend.claudeConnected ? Theme.cyan : Theme.amber
            highlighted: !backend.claudeConnected
            ColumnLayout {
                id: claudeCol
                anchors.left: parent.left; anchors.right: parent.right
                spacing: 6
                RowLayout {
                    spacing: 8
                    Rectangle { width: 10; height: 10; radius: 5; color: backend.claudeConnected ? Theme.green : Theme.amber }
                    Text { text: backend.providerName || "Claude Code"; color: Theme.text; font.family: Theme.font; font.pixelSize: 14; font.weight: Font.DemiBold }
                    Item { Layout.fillWidth: true }
                    HudButton { icon: "⟳"; implicitHeight: 26; implicitWidth: 30; onClicked: backend.refreshClaude() }
                }
                Text { text: backend.claudeStatus; color: backend.claudeConnected ? Theme.green : Theme.amber; font.family: Theme.mono; font.pixelSize: 12 }
                Text { text: backend.claudeDetail; color: Theme.muted; font.family: Theme.font; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true; visible: text.length > 0 }
                Rectangle {
                    visible: backend.claudeHint.length > 0
                    Layout.fillWidth: true
                    Layout.preferredHeight: hint.implicitHeight + 16
                    radius: 6
                    color: Theme.alpha(Theme.amber, 0.08)
                    border.color: Theme.alpha(Theme.amber, 0.35)
                    TextEdit {
                        id: hint
                        anchors.fill: parent; anchors.margins: 8
                        text: backend.claudeHint
                        color: Theme.text; font.family: Theme.mono; font.pixelSize: 11
                        wrapMode: Text.WordWrap; readOnly: true; selectByMouse: true
                    }
                }
            }
        }

        // Claude usage ------------------------------------------------------
        HolographicPanel {
            id: usageCard
            Layout.fillWidth: true
            Layout.preferredHeight: usageCol.implicitHeight + 54
            title: "Claude Kullanımı"
            tag: "VOLB"
            readonly property var five: backend.rateLimits.find(l => l.rateLimitType === "five_hour")
            property real nowMs: Date.now()
            Timer { interval: 30000; running: true; repeat: true; onTriggered: usageCard.nowMs = Date.now() }
            accent: five ? Theme.limitColor(five.status) === Theme.green ? Theme.cyan : Theme.limitColor(five.status) : Theme.cyan
            ColumnLayout {
                id: usageCol
                anchors.left: parent.left; anchors.right: parent.right
                spacing: 6
                RowLayout {
                    Layout.fillWidth: true
                    Rectangle { width: 8; height: 8; radius: 4; color: usageCard.five ? Theme.limitColor(usageCard.five.status) : Theme.dim }
                    Text {
                        text: usageCard.five ? "5 sa: " + Theme.limitStatus(usageCard.five.status) : "Limit bilgisi henüz yok"
                        color: Theme.text; font.family: Theme.font; font.pixelSize: 12; Layout.fillWidth: true
                    }
                    Text {
                        visible: !!usageCard.five
                        text: usageCard.five ? "↻ " + Theme.countdown(usageCard.five.resetsAt, usageCard.nowMs) : ""
                        color: Theme.muted; font.family: Theme.mono; font.pixelSize: 11
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    Repeater {
                        model: [{ l: "SON 5 SA", k: "last5h" }, { l: "BUGÜN", k: "today" }, { l: "7 GÜN", k: "week" }]
                        Column {
                            Layout.fillWidth: true
                            readonly property var w: (backend.usage || {})[modelData.k] || {}
                            Text { text: modelData.l; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 9; font.letterSpacing: 1 }
                            Text { text: Theme.fmtTokens(parent.w.total); color: Theme.cyan; font.family: Theme.mono; font.pixelSize: 15; font.bold: true }
                            Text { text: (parent.w.calls || 0) + " istek"; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 9 }
                        }
                    }
                }
            }
            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: win.page = 7 }
        }

        // Resources ---------------------------------------------------------
        HolographicPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 196
            title: "Kaynaklar"
            tag: backend.uptimeText ? "UP " + backend.uptimeText : ""
            RowLayout {
                anchors.left: parent.left; anchors.right: parent.right
                spacing: 4
                Repeater {
                    model: [
                        { label: "CPU", value: backend.cpu, detail: backend.cpuText },
                        { label: "RAM", value: backend.ram, detail: backend.ramText },
                        { label: "DİSK", value: backend.disk, detail: backend.diskText }
                    ]
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 4
                        RingGauge { Layout.alignment: Qt.AlignHCenter; implicitWidth: 80; implicitHeight: 80; value: modelData.value; label: modelData.label }
                        Text { Layout.alignment: Qt.AlignHCenter; text: modelData.detail; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter
                               Layout.maximumWidth: 86; elide: Text.ElideRight }
                    }
                }
            }
            Text {
                anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right
                text: backend.gpuText; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 10; elide: Text.ElideRight
            }
        }

        // Microphone --------------------------------------------------------
        HolographicPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 128
            title: "Mikrofon"
            tag: backend.continuous ? "SÜREKLİ" : "BAS-KONUŞ"
            accent: backend.listening ? Theme.cyan : Theme.blue
            ColumnLayout {
                anchors.left: parent.left; anchors.right: parent.right
                spacing: 8
                Text { text: backend.micStatus; color: Theme.text; font.family: Theme.font; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
                Rectangle {
                    Layout.fillWidth: true; height: 6; radius: 3
                    color: Theme.alpha(Theme.cyan, 0.1)
                    Rectangle { height: parent.height; radius: 3; width: parent.width * backend.micLevel; color: backend.micLevel > 0.8 ? Theme.amber : Theme.cyan
                                Behavior on width { NumberAnimation { duration: 60 } } }
                }
                Text { text: backend.voiceStatus || (backend.sttStatus + "  •  TTS: " + backend.ttsStatus); color: Theme.muted; font.family: Theme.font; font.pixelSize: 11
                       elide: Text.ElideRight; Layout.fillWidth: true }
            }
        }

        // Active task -------------------------------------------------------
        HolographicPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 104
            title: "Aktif Görev"
            accent: backend.busy ? Theme.amber : Theme.cyan
            ColumnLayout {
                anchors.left: parent.left; anchors.right: parent.right
                spacing: 6
                Text { text: backend.activeTask; color: Theme.text; font.family: Theme.font; font.pixelSize: 13; elide: Text.ElideRight; Layout.fillWidth: true }
                Text { text: backend.activity; color: Theme.muted; font.family: Theme.font; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                Rectangle {
                    Layout.fillWidth: true; height: 3; radius: 1.5; clip: true
                    color: Theme.alpha(Theme.cyan, 0.1)
                    visible: backend.busy
                    Rectangle {
                        width: parent.width * 0.3; height: parent.height; radius: 1.5; color: Theme.amber
                        SequentialAnimation on x { loops: Animation.Infinite; running: backend.busy
                            NumberAnimation { from: -80; to: 280; duration: 1200; easing.type: Easing.InOutQuad } }
                    }
                }
            }
        }

        // Recent actions ----------------------------------------------------
        HolographicPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(120, recentCol.implicitHeight + 56)
            title: "Son İşlemler"
            Column {
                id: recentCol
                anchors.left: parent.left; anchors.right: parent.right
                spacing: 6
                Text { visible: backend.recentActions.length === 0; text: "Henüz işlem yok."; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
                Repeater {
                    model: backend.recentActions.slice(0, 7)
                    Row {
                        width: recentCol.width
                        spacing: 8
                        Text { text: modelData.time; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter }
                        Rectangle { width: 5; height: 5; radius: 2.5; color: modelData.ok ? Theme.green : Theme.red; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: modelData.text; color: Theme.muted; font.family: Theme.font; font.pixelSize: 11; width: parent.width - 60; elide: Text.ElideRight }
                    }
                }
            }
        }
    }
}
