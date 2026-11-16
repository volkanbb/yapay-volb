import QtQuick
import QtQuick.Layouts

// Voice + text command bar.
HolographicPanel {
    id: root
    padding: 12
    accent: backend.listening ? Theme.cyan : Theme.blue
    highlighted: backend.listening

    RowLayout {
        anchors.fill: parent
        spacing: 10

        // push-to-talk mic button with level ring
        Item {
            Layout.preferredWidth: 48; Layout.preferredHeight: 48
            Rectangle {
                anchors.centerIn: parent
                width: 48 + backend.micLevel * 16 * (backend.listening ? 1 : 0); height: width; radius: width / 2
                color: "transparent"
                border.color: Theme.alpha(Theme.cyan, 0.5); border.width: 2
                opacity: backend.listening ? 1 : 0
                Behavior on width { NumberAnimation { duration: 70 } }
            }
            Rectangle {
                id: micBtn
                anchors.fill: parent
                radius: width / 2
                color: backend.listening ? Theme.cyan : micMa.containsMouse ? Theme.alpha(Theme.cyan, 0.28) : Theme.alpha(Theme.cyan, 0.14)
                border.color: Theme.cyan; border.width: 1.5
                Text { anchors.centerIn: parent; text: "🎙"; font.pixelSize: 20; color: backend.listening ? Theme.bg : Theme.cyan }
                MouseArea {
                    id: micMa
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onPressed: backend.pttPressed()
                    onReleased: backend.pttReleased()
                    onCanceled: backend.pttReleased()
                }
            }
        }
        Column {
            spacing: 4
            Layout.preferredWidth: 78
            Text { text: backend.listening ? "DİNLİYOR" : "BASILI TUT"; color: backend.listening ? Theme.cyan : Theme.muted; font.family: Theme.mono; font.pixelSize: 10; font.letterSpacing: 1 }
            Row {
                spacing: 6
                HudSwitch { checked: backend.continuous; onToggled: (v) => backend.setContinuous(v); implicitWidth: 34; implicitHeight: 18 }
                Text { text: "Sürekli"; color: Theme.muted; font.family: Theme.font; font.pixelSize: 11; anchors.verticalCenter: parent.verticalCenter }
            }
        }

        HudField {
            id: input
            Layout.fillWidth: true
            Layout.preferredHeight: 46
            font.pixelSize: 15
            placeholderText: "VOLB'a bir şey söyle…  (örn. \"Volb, Blender'ı başlat\" veya \"yapay zekâ haberlerini araştır\")"
            onAccepted: send()
            function send() {
                if (text.trim().length === 0) return
                backend.sendText(text)
                text = ""
            }
        }
        HudButton { text: "Gönder"; icon: "➤"; primary: true; implicitHeight: 46; onClicked: input.send() }

        VoiceVisualizer {
            Layout.preferredWidth: 190
            Layout.preferredHeight: 44
            visible: root.width > 900
            bars: 36
            level: backend.speaking ? Math.max(backend.speechLevel, 0.45) : backend.micLevel
            active: backend.speaking || backend.listening || backend.continuous
            color: backend.speaking ? "#5CF2FF" : Theme.cyan
        }
        HudButton { icon: "■"; text: root.width > 1100 ? "Sustur" : ""; danger: backend.speaking; implicitHeight: 46; onClicked: backend.stopSpeaking() }
        HudButton { icon: "✕"; implicitHeight: 46; implicitWidth: 46; enabledState: backend.busy; onClicked: backend.stopAll() }
    }
}
