import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import "../components"

HolographicPanel {
    id: root
    title: "AI Sohbet"
    tag: backend.providerName

    HudButton {
        anchors.right: parent.right; y: -30
        text: "Sohbeti temizle"; icon: "⌫"; implicitHeight: 26
        onClicked: backend.clearChat()
    }

    RowLayout {
        anchors.fill: parent
        spacing: 14

        Item {
            Layout.preferredWidth: 150
            Layout.fillHeight: true
            visible: root.width > 760
            VolbCharacter {
                width: 150; height: 180
                mood: backend.state
                micLevel: backend.micLevel
                speechLevel: backend.speechLevel
                compact: true
            }
            Text {
                y: 186; width: 150; horizontalAlignment: Text.AlignHCenter
                text: Theme.stateLabel(backend.state)
                color: Theme.stateColor(backend.state)
                font.family: Theme.mono; font.pixelSize: 11; font.letterSpacing: 2
            }
        }

        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 12
            model: chatModel
            ScrollBar.vertical: ScrollBar { width: 6 }
            delegate: MessageBubble {
                width: list.width - 10
                maxWidth: Math.min(760, list.width * 0.82)
                role: model.role; text: model.text; time: model.time; done: model.done
            }
            onCountChanged: Qt.callLater(positionViewAtEnd)
            Component.onCompleted: positionViewAtEnd()
            Connections {
                target: chatModel
                function onDataChanged() { if (list.atYEnd || list.contentHeight - list.contentY - list.height < 200) Qt.callLater(list.positionViewAtEnd) }
            }
            Text {
                anchors.centerIn: parent
                visible: list.count === 0
                text: "Henüz mesaj yok. Alttaki kutuya yaz ya da mikrofona basılı tut."
                color: Theme.muted; font.family: Theme.font; font.pixelSize: 14
            }
        }
    }
}
