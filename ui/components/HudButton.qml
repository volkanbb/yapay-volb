import QtQuick

// Compact futuristic button.
Rectangle {
    id: root
    property string text: ""
    property string icon: ""
    property color accent: Theme.cyan
    property bool primary: false
    property bool danger: false
    property bool checked: false
    property bool enabledState: true
    signal clicked()
    signal pressed()
    signal released()

    readonly property color tone: danger ? Theme.red : accent
    implicitWidth: Math.max(36, row.implicitWidth + 24)
    implicitHeight: 34
    radius: 8
    opacity: enabledState ? 1 : 0.4
    color: primary || checked ? Theme.alpha(tone, ma.pressed ? 0.42 : ma.containsMouse ? 0.32 : 0.22)
                              : Theme.alpha(tone, ma.pressed ? 0.2 : ma.containsMouse ? 0.12 : 0.05)
    border.width: 1
    border.color: Theme.alpha(tone, ma.containsMouse || checked || primary ? 0.8 : 0.35)
    Behavior on color { ColorAnimation { duration: 120 } }

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 7
        Text {
            visible: root.icon.length > 0
            text: root.icon
            color: root.tone
            font.pixelSize: 15
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            visible: root.text.length > 0
            text: root.text
            color: Theme.text
            font.family: Theme.font; font.pixelSize: 13; font.weight: Font.Medium
            anchors.verticalCenter: parent.verticalCenter
        }
    }
    MouseArea {
        id: ma
        anchors.fill: parent
        hoverEnabled: true
        enabled: root.enabledState
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
        onPressed: root.pressed()
        onReleased: root.released()
        onCanceled: root.released()
    }
}
