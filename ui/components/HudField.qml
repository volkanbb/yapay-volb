import QtQuick
import QtQuick.Controls.Basic

// Styled single-line text input.
TextField {
    id: root
    property color accent: Theme.cyan
    color: Theme.text
    placeholderTextColor: Theme.muted
    selectionColor: Theme.alpha(Theme.cyan, 0.4)
    selectedTextColor: Theme.text
    font.family: Theme.font
    font.pixelSize: 14
    leftPadding: 14; rightPadding: 14
    implicitHeight: 40
    background: Rectangle {
        radius: 8
        color: Qt.rgba(0.02, 0.04, 0.07, 0.9)
        border.width: 1
        border.color: root.activeFocus ? Theme.alpha(root.accent, 0.85) : Theme.alpha(root.accent, 0.25)
        Behavior on border.color { ColorAnimation { duration: 150 } }
    }
}
