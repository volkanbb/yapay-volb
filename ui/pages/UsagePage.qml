import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import "../components"

// Claude Code token usage of YAPAY VOLB + subscription rate-limit status reported by the CLI.
Flickable {
    id: root
    contentHeight: col.implicitHeight + 20
    clip: true
    ScrollBar.vertical: ScrollBar { width: 6 }

    readonly property var u: backend.usage || {}
    property real nowMs: Date.now()
    Timer { interval: 30000; running: root.visible; repeat: true; onTriggered: root.nowMs = Date.now() }
    onVisibleChanged: if (visible) { nowMs = Date.now(); backend.refreshUsage() }

    component Stat: Column {
        property string label: ""
        property string value: ""
        property string sub: ""
        property color tone: Theme.cyan
        spacing: 2
        Text { text: parent.label; color: Theme.muted; font.family: Theme.font; font.pixelSize: 11; font.letterSpacing: 1.5 }
        Text { text: parent.value; color: parent.tone; font.family: Theme.mono; font.pixelSize: 24; font.bold: true }
        Text { text: parent.sub; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 10; visible: text.length > 0 }
    }

    ColumnLayout {
        id: col
        width: root.width - 12
        spacing: 12

        // ---------------------------------------------------------------- limits
        HolographicPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: limitsCol.implicitHeight + 58
            title: "Claude Pro limitleri"
            tag: "Claude Code CLI bildirir"
            accent: backend.rateLimits.some(l => l.status === "rejected") ? Theme.red
                  : backend.rateLimits.some(l => l.status === "allowed_warning") ? Theme.amber : Theme.cyan
            ColumnLayout {
                id: limitsCol
                anchors.left: parent.left; anchors.right: parent.right
                spacing: 10
                Text {
                    visible: backend.rateLimits.length === 0
                    Layout.fillWidth: true; wrapMode: Text.WordWrap
                    text: "Henüz limit bilgisi yok. Claude'a bir şey sorduğunda CLI limit durumunu bildirir; ya da aşağıdaki düğmeyle kontrol et."
                    color: Theme.muted; font.family: Theme.font; font.pixelSize: 13
                }
                Repeater {
                    model: backend.rateLimits
                    Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: lrow.implicitHeight + 20
                        radius: 8
                        color: Qt.rgba(0.03, 0.07, 0.12, 0.9)
                        border.color: Theme.alpha(Theme.limitColor(modelData.status), 0.5)
                        RowLayout {
                            id: lrow
                            anchors.fill: parent; anchors.margins: 10
                            spacing: 16
                            Rectangle { width: 12; height: 12; radius: 6; color: Theme.limitColor(modelData.status) }
                            Column {
                                Layout.fillWidth: true
                                spacing: 3
                                Text { text: Theme.limitLabel(modelData.rateLimitType); color: Theme.text; font.family: Theme.font; font.pixelSize: 15; font.weight: Font.DemiBold }
                                Text {
                                    text: Theme.limitStatus(modelData.status)
                                          + (modelData.utilization !== undefined ? "  •  kullanım %" + Math.round(modelData.utilization > 1 ? modelData.utilization : modelData.utilization * 100) : "")
                                    color: Theme.limitColor(modelData.status); font.family: Theme.font; font.pixelSize: 13
                                }
                                Text {
                                    text: "Ek ücretli kullanım (overage): " + (modelData.isUsingOverage ? "KULLANILIYOR" : modelData.overageStatus === "rejected" ? "kapalı" : (modelData.overageStatus || "—"))
                                    color: modelData.isUsingOverage ? Theme.amber : Theme.dim; font.family: Theme.font; font.pixelSize: 11
                                }
                            }
                            Column {
                                spacing: 2
                                Text { anchors.right: parent.right; text: "SIFIRLANMA"; color: Theme.muted; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1.5 }
                                Text { anchors.right: parent.right; text: Theme.countdown(modelData.resetsAt, root.nowMs); color: Theme.text; font.family: Theme.mono; font.pixelSize: 18; font.bold: true }
                                Text { anchors.right: parent.right
                                       text: modelData.resetsAt ? Qt.formatDateTime(new Date(modelData.resetsAt * 1000), "dd.MM HH:mm") : ""
                                       color: Theme.dim; font.family: Theme.mono; font.pixelSize: 10 }
                            }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    HudButton {
                        text: backend.limitChecking ? "Kontrol ediliyor…" : "Limitleri şimdi kontrol et"
                        icon: "⟳"
                        enabledState: !backend.limitChecking && backend.claudeConnected
                        onClicked: backend.probeLimits()
                    }
                    Text {
                        Layout.fillWidth: true; wrapMode: Text.WordWrap
                        text: "Kontrol, Haiku ile çok küçük bir istek gönderir (kotandan çok az harcar). Claude Code CLI kalan yüzdeyi genelde yalnızca limite yaklaşınca bildirir; tam yüzde için Claude Code'da /usage komutunu kullanabilirsin."
                        color: Theme.dim; font.family: Theme.font; font.pixelSize: 11
                    }
                }
            }
        }

        // ---------------------------------------------------------------- totals
        HolographicPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 150
            title: "VOLB'un harcadığı tokenler"
            tag: "giriş + önbellek + çıkış"
            GridLayout {
                anchors.fill: parent
                columns: 4
                columnSpacing: 20
                Repeater {
                    model: [
                        { label: "SON 5 SAAT", key: "last5h" },
                        { label: "BUGÜN", key: "today" },
                        { label: "SON 7 GÜN", key: "week" },
                        { label: "TÜM ZAMANLAR", key: "all" }
                    ]
                    Stat {
                        Layout.fillWidth: true
                        readonly property var w: root.u[modelData.key] || {}
                        label: modelData.label
                        value: Theme.fmtTokens(w.total)
                        sub: (w.calls || 0) + " istek • çıkış " + Theme.fmtTokens(w.output) + " • ≈" + Theme.fmtUsd(w.cost)
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            // daily chart
            HolographicPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: 230
                title: "Son 7 gün"
                Row {
                    id: bars
                    anchors.fill: parent
                    anchors.bottomMargin: 18
                    spacing: 10
                    readonly property var days: root.u.daily || []
                    readonly property real peak: Math.max(1, ...days.map(d => d.total))
                    Repeater {
                        model: bars.days
                        Item {
                            width: (bars.width - bars.spacing * 6) / 7
                            height: bars.height
                            Rectangle {
                                anchors.bottom: parent.bottom
                                width: parent.width; radius: 4
                                height: Math.max(2, (parent.height - 18) * modelData.total / bars.peak)
                                gradient: Gradient {
                                    GradientStop { position: 0; color: Theme.cyan }
                                    GradientStop { position: 1; color: Theme.alpha(Theme.blue, 0.5) }
                                }
                                Behavior on height { NumberAnimation { duration: 400 } }
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter
                                y: parent.height - Math.max(2, (parent.height - 18) * modelData.total / bars.peak) - 16
                                text: modelData.total ? Theme.fmtTokens(modelData.total) : ""
                                color: Theme.muted; font.family: Theme.mono; font.pixelSize: 9
                            }
                            Text {
                                anchors.horizontalCenter: parent.horizontalCenter; y: parent.height + 4
                                text: modelData.day; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 10
                            }
                        }
                    }
                }
            }

            // breakdown
            HolographicPanel {
                Layout.fillWidth: true
                Layout.preferredHeight: 230
                title: "Dağılım"
                tag: "son 7 gün"
                Column {
                    anchors.left: parent.left; anchors.right: parent.right
                    spacing: 6
                    Text { text: "AMAÇ"; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 10; font.letterSpacing: 1.5 }
                    Repeater {
                        model: root.u.byPurpose || []
                        RowLayout {
                            width: parent.width
                            Text { text: modelData.purpose; color: Theme.text; font.family: Theme.font; font.pixelSize: 12; Layout.fillWidth: true }
                            Text { text: modelData.calls + " istek"; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 11 }
                            Text { text: Theme.fmtTokens(modelData.total); color: Theme.cyan; font.family: Theme.mono; font.pixelSize: 12; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
                        }
                    }
                    Item { width: 1; height: 6 }
                    Text { text: "MODEL"; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 10; font.letterSpacing: 1.5 }
                    Repeater {
                        model: root.u.byModel || []
                        RowLayout {
                            width: parent.width
                            Text { text: modelData.model; color: Theme.text; font.family: Theme.mono; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight }
                            Text { text: "çıkış " + Theme.fmtTokens(modelData.output); color: Theme.dim; font.family: Theme.mono; font.pixelSize: 11 }
                            Text { text: Theme.fmtTokens(modelData.total); color: Theme.cyan; font.family: Theme.mono; font.pixelSize: 12; Layout.preferredWidth: 70; horizontalAlignment: Text.AlignRight }
                        }
                    }
                    Text { visible: (root.u.byModel || []).length === 0; text: "Henüz kayıt yok."; color: Theme.dim; font.family: Theme.font; font.pixelSize: 12 }
                }
            }
        }

        // ---------------------------------------------------------------- recent calls
        HolographicPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 70 + Math.max(1, (root.u.recent || []).length) * 24
            title: "Son istekler"
            Column {
                anchors.left: parent.left; anchors.right: parent.right
                spacing: 4
                RowLayout {
                    width: parent.width
                    Repeater {
                        model: ["ZAMAN", "AMAÇ", "MODEL", "GİRİŞ", "ÖNBELLEK", "ÇIKIŞ", "≈$"]
                        Text { text: modelData; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 10
                               Layout.preferredWidth: index === 2 ? 220 : index === 1 ? 120 : 90; Layout.fillWidth: index === 2 }
                    }
                }
                Repeater {
                    model: root.u.recent || []
                    RowLayout {
                        width: parent.width
                        Text { text: modelData.time; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 11; Layout.preferredWidth: 90 }
                        Text { text: modelData.purpose; color: Theme.text; font.family: Theme.font; font.pixelSize: 12; Layout.preferredWidth: 120 }
                        Text { text: modelData.model; color: Theme.text; font.family: Theme.mono; font.pixelSize: 11; Layout.preferredWidth: 220; Layout.fillWidth: true; elide: Text.ElideRight }
                        Text { text: Theme.fmtTokens(modelData.input); color: Theme.muted; font.family: Theme.mono; font.pixelSize: 11; Layout.preferredWidth: 90 }
                        Text { text: Theme.fmtTokens(modelData.cache_read + modelData.cache_write); color: Theme.muted; font.family: Theme.mono; font.pixelSize: 11; Layout.preferredWidth: 90 }
                        Text { text: Theme.fmtTokens(modelData.output); color: Theme.cyan; font.family: Theme.mono; font.pixelSize: 11; Layout.preferredWidth: 90 }
                        Text { text: Number(modelData.cost_usd).toFixed(3); color: Theme.muted; font.family: Theme.mono; font.pixelSize: 11; Layout.preferredWidth: 90 }
                    }
                }
            }
        }

        Text {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "Not: Claude Pro aboneliğinde istek başına ücret ödemezsin. “≈$” değeri, aynı kullanımın ücretli API'de ne tutacağının Claude Code tarafından hesaplanan tahminidir. Önbellekten okunan tokenler (VOLB'un sabit sistem talimatı) her istekte tekrar gönderilir ama çok daha ucuz sayılır."
            color: Theme.dim; font.family: Theme.font; font.pixelSize: 11
        }
    }
}
