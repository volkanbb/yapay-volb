import QtQuick

// Dark glass panel with thin glowing border, corner brackets and an optional HUD title.
Item {
    id: root
    property string title: ""
    property string tag: ""
    property color accent: Theme.cyan
    property real padding: 14
    property bool highlighted: false
    property real radius: 10
    default property alias content: body.data
    readonly property alias body: body

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: root.radius
        gradient: Gradient {
            GradientStop { position: 0.0; color: Qt.rgba(0.055, 0.10, 0.16, 0.86) }
            GradientStop { position: 1.0; color: Qt.rgba(0.035, 0.065, 0.105, 0.86) }
        }
        border.width: 1
        border.color: Theme.alpha(root.accent, root.highlighted ? 0.55 : 0.2)
        Behavior on border.color { ColorAnimation { duration: 250 } }
    }

    // top light streak
    Rectangle {
        x: root.radius + 6; y: 0
        width: Math.min(parent.width * 0.38, 160); height: 1
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: Theme.alpha(root.accent, 0.9) }
            GradientStop { position: 1; color: Theme.alpha(root.accent, 0) }
        }
    }

    // corner brackets
    Repeater {
        model: 4
        Item {
            readonly property bool atRight: index % 2 === 1
            readonly property bool atBottom: index > 1
            width: 10; height: 10
            x: atRight ? root.width - width - 3 : 3
            y: atBottom ? root.height - height - 3 : 3
            Rectangle { width: 10; height: 1.5; color: Theme.alpha(root.accent, 0.75); y: parent.atBottom ? 8.5 : 0 }
            Rectangle { width: 1.5; height: 10; color: Theme.alpha(root.accent, 0.75); x: parent.atRight ? 8.5 : 0 }
        }
    }

    Row {
        id: header
        visible: root.title.length > 0
        x: root.padding; y: 12
        spacing: 8
        Rectangle { width: 6; height: 6; radius: 1; rotation: 45; color: root.accent; anchors.verticalCenter: parent.verticalCenter }
        Text {
            text: root.title.toUpperCase()
            color: Theme.text
            font.family: Theme.font; font.pixelSize: 12; font.weight: Font.DemiBold; font.letterSpacing: 2
        }
        Text {
            visible: root.tag.length > 0
            text: root.tag
            color: Theme.muted
            font.family: Theme.mono; font.pixelSize: 10
            anchors.verticalCenter: parent.verticalCenter
        }
    }

    Item {
        id: body
        anchors.fill: parent
        anchors.margins: root.padding
        anchors.topMargin: root.title.length > 0 ? 38 : root.padding
    }
}
