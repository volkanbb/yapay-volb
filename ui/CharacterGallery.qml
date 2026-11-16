import QtQuick
import QtQuick.Window
import "components"

// Developer gallery: every VOLB state side by side (python tools/render_gallery.py).
Window {
    width: 1500; height: 560; visible: true; color: Theme.bg
    title: "VOLB states"
    Row {
        anchors.fill: parent
        Repeater {
            model: ["idle", "listening", "thinking", "speaking", "working", "error"]
            Item {
                width: 250; height: 560
                VolbCharacter { anchors.fill: parent; anchors.bottomMargin: 40; mood: modelData; micLevel: 0.6; speechLevel: 0 }
                Text { anchors.bottom: parent.bottom; anchors.bottomMargin: 12; anchors.horizontalCenter: parent.horizontalCenter
                       text: Theme.stateLabel(modelData); color: Theme.stateColor(modelData); font.pixelSize: 16; font.bold: true }
            }
        }
    }
}
