import QtQuick
import QtQuick.Layouts
import "../components"

// Center stage: VOLB, state indicator, activity, audio visualization, last reply.
Item {
    id: root

    VolbCharacter {
        id: volb
        anchors.horizontalCenter: parent.horizontalCenter
        y: 40
        width: parent.width
        height: parent.height - 220
        mood: backend.state
        micLevel: backend.micLevel
        speechLevel: backend.speechLevel
    }

    // state indicator
    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        y: 4
        spacing: 6
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            implicitWidth: stateRow.implicitWidth + 28; implicitHeight: 32; radius: 16
            color: Theme.alpha(Theme.stateColor(backend.state), 0.12)
            border.color: Theme.alpha(Theme.stateColor(backend.state), 0.7)
            Behavior on color { ColorAnimation { duration: 300 } }
            Row {
                id: stateRow
                anchors.centerIn: parent
                spacing: 10
                Rectangle {
                    width: 9; height: 9; radius: 4.5; anchors.verticalCenter: parent.verticalCenter
                    color: Theme.stateColor(backend.state)
                    SequentialAnimation on scale { loops: Animation.Infinite; NumberAnimation { to: 1.5; duration: 700 } NumberAnimation { to: 1; duration: 700 } }
                }
                Text { text: Theme.stateLabel(backend.state); color: Theme.stateColor(backend.state); font.family: Theme.mono; font.pixelSize: 14; font.bold: true; font.letterSpacing: 3 }
            }
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: backend.activity
            color: Theme.muted
            font.family: Theme.font; font.pixelSize: 13
            width: Math.min(implicitWidth, root.width - 40); elide: Text.ElideRight
        }
    }

    // HUD corner decorations
    Column {
        x: 8; y: 8; spacing: 3
        Repeater {
            model: ["VOLB//CORE", "NODE " + Qt.platform.os.toUpperCase(), "LINK " + (backend.claudeConnected ? "SECURE" : "PENDING")]
            Text { text: modelData; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 10; font.letterSpacing: 1.5 }
        }
    }
    Column {
        anchors.right: parent.right; anchors.rightMargin: 8; y: 8; spacing: 3
        Repeater {
            model: ["CPU " + Math.round(backend.cpu * 100) + "%", "RAM " + Math.round(backend.ram * 100) + "%", "MIC " + (backend.continuous ? "AÇIK" : "PTT")]
            Text { anchors.right: parent.right; text: modelData; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 10; font.letterSpacing: 1.5 }
        }
    }

    // audio + last reply
    ColumnLayout {
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        anchors.leftMargin: 10; anchors.rightMargin: 10
        spacing: 10

        VoiceVisualizer {
            Layout.fillWidth: true
            Layout.preferredHeight: 46
            Layout.maximumWidth: 720
            Layout.alignment: Qt.AlignHCenter
            bars: 64
            level: backend.speaking ? Math.max(backend.speechLevel, 0.5) : backend.listening ? backend.micLevel : backend.state === "thinking" ? 0.18 : 0
            color: Theme.stateColor(backend.state)
        }

        HolographicPanel {
            Layout.fillWidth: true
            Layout.maximumWidth: 900
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredHeight: 104
            title: "VOLB"
            tag: "son yanıt"
            Flickable {
                anchors.fill: parent
                contentHeight: replyText.implicitHeight
                clip: true
                Text {
                    id: replyText
                    width: parent.width
                    text: backend.lastReply.length ? backend.lastReply : "Selam, ben VOLB. Mikrofona basılı tutup konuş ya da aşağıya yaz."
                    color: backend.lastReply.length ? Theme.text : Theme.muted
                    textFormat: Text.MarkdownText
                    wrapMode: Text.WordWrap
                    font.family: Theme.font; font.pixelSize: 14
                    onLinkActivated: (l) => backend.openExternal(l)
                }
            }
        }

        Flow {
            Layout.fillWidth: true
            Layout.maximumWidth: 900
            Layout.alignment: Qt.AlignHCenter
            spacing: 8
            Repeater {
                model: ["Google'ı aç", "RAM kullanımımı göster", "Bugün yapay zekâ haberlerini araştır", "10 dakika sonra bana su içmeyi hatırlat", "Blender'ı başlat"]
                HudButton { text: modelData; implicitHeight: 28; onClicked: backend.sendText("Volb, " + modelData) }
            }
        }
    }
}
