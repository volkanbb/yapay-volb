import QtQuick

// Minimal toggle switch.
Item {
    id: root
    property bool checked: false
    property color accent: Theme.cyan
    signal toggled(bool value)
    implicitWidth: 46; implicitHeight: 24
    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: root.checked ? Theme.alpha(root.accent, 0.35) : Qt.rgba(1, 1, 1, 0.06)
        border.color: root.checked ? root.accent : Theme.alpha(Theme.muted, 0.5)
        border.width: 1
        Behavior on color { ColorAnimation { duration: 150 } }
        Rectangle {
            width: parent.height - 6; height: width; radius: width / 2
            y: 3
            x: root.checked ? parent.width - width - 3 : 3
            color: root.checked ? root.accent : Theme.muted
            Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
        }
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.toggled(!root.checked)
    }
}
