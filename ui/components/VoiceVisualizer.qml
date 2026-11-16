import QtQuick

// Mirrored bar waveform driven by an audio level (0..1).
Item {
    id: root
    property real level: 0
    property bool active: true
    property int bars: 48
    property color color: Theme.cyan
    property color color2: Theme.blue
    property real gap: 3
    property real idleAmplitude: 0.06
    property real t: 0
    property real smooth: 0

    implicitHeight: 60

    FrameAnimation {
        running: root.visible
        onTriggered: {
            root.t += frameTime
            const target = root.active ? root.level : 0
            root.smooth += (target - root.smooth) * Math.min(1, frameTime * 14)
        }
    }

    Row {
        anchors.centerIn: parent
        spacing: root.gap
        Repeater {
            model: root.bars
            Rectangle {
                readonly property real u: index / (root.bars - 1)
                readonly property real envelope: Math.pow(Math.sin(Math.PI * u), 0.8)
                readonly property real wobble: 0.35 + 0.65 * Math.abs(Math.sin(root.t * 6.3 + index * 0.55) * Math.cos(root.t * 2.1 + index * 0.27))
                readonly property real amp: root.idleAmplitude * (0.6 + 0.4 * Math.sin(root.t * 1.7 + index * 0.4)) + root.smooth * wobble
                width: Math.max(2, (root.width - root.gap * (root.bars - 1)) / root.bars)
                height: Math.max(2, root.height * Math.min(1, amp * envelope * 1.15))
                radius: width / 2
                anchors.verticalCenter: parent.verticalCenter
                color: Qt.rgba(root.color.r * (1 - u) + root.color2.r * u,
                               root.color.g * (1 - u) + root.color2.g * u,
                               root.color.b * (1 - u) + root.color2.b * u, 0.45 + 0.55 * envelope)
            }
        }
    }
}
