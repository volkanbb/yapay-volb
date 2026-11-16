import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import "../components"

HolographicPanel {
    id: root
    title: "Hafıza"
    tag: backend.memories.length + " kayıt • SQLite"
    property bool confirmWipe: false

    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            HudField {
                id: newMem
                Layout.fillWidth: true
                placeholderText: "VOLB'un hatırlamasını istediğin bir bilgi… (veya sohbette: \"hatırla: …\")"
                onAccepted: add()
                function add() { if (text.trim()) { backend.addMemory(text); text = "" } }
            }
            HudButton { text: "Ekle"; icon: "+"; primary: true; implicitHeight: 40; onClicked: newMem.add() }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            HudButton {
                text: "Tümünü dışa aktar (JSON)"; icon: "⇩"; implicitHeight: 30
                onClicked: { const p = backend.exportMemory(); exportPath.text = p }
            }
            Text { id: exportPath; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideMiddle
                   MouseArea { anchors.fill: parent; enabled: exportPath.text.length > 0; cursorShape: Qt.PointingHandCursor; onClicked: backend.openPath(exportPath.text) } }
            HudButton {
                text: root.confirmWipe ? "Emin misin? Tekrar bas" : "Tüm kişisel verileri sil"
                danger: true; implicitHeight: 30
                onClicked: {
                    if (root.confirmWipe) { backend.wipePersonalData(); root.confirmWipe = false }
                    else { root.confirmWipe = true; wipeReset.restart() }
                }
                Timer { id: wipeReset; interval: 4000; onTriggered: root.confirmWipe = false }
            }
        }
        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 8
            model: backend.memories
            ScrollBar.vertical: ScrollBar { width: 6 }
            delegate: Rectangle {
                width: list.width - 8; height: 56; radius: 8
                color: Qt.rgba(0.03, 0.07, 0.12, 0.9); border.color: Theme.border
                RowLayout {
                    anchors.fill: parent; anchors.margins: 8
                    spacing: 10
                    Text { text: "◆"; color: Theme.cyan; font.pixelSize: 12 }
                    HudField {
                        id: edit
                        Layout.fillWidth: true
                        text: modelData.content
                        implicitHeight: 38
                        onAccepted: backend.updateMemory(modelData.id, text)
                    }
                    Text { text: modelData.date; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 10 }
                    HudButton { text: "Kaydet"; implicitHeight: 30; enabledState: edit.text !== modelData.content; onClicked: backend.updateMemory(modelData.id, edit.text) }
                    HudButton { icon: "🗑"; danger: true; implicitHeight: 30; implicitWidth: 34; onClicked: backend.deleteMemory(modelData.id) }
                }
            }
            Text {
                anchors.centerIn: parent
                visible: list.count === 0
                text: "Hafıza boş. Tercihlerini, projelerini veya önemli bilgileri ekleyebilirsin."
                color: Theme.muted; font.family: Theme.font; font.pixelSize: 14
            }
        }
    }
}
