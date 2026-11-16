import QtQuick
import QtQuick.Shapes

// Circular HUD gauge (value 0..1).
Item {
    id: root
    property real value: 0
    property string label: ""
    property string detail: ""
    property color accent: value > 0.85 ? Theme.red : value > 0.7 ? Theme.amber : Theme.cyan
    property real thickness: 6
    implicitWidth: 92; implicitHeight: 92

    property real shown: 0
    Behavior on shown { NumberAnimation { duration: 600; easing.type: Easing.OutCubic } }
    onValueChanged: shown = value
    Component.onCompleted: shown = value

    readonly property real r: Math.min(width, height) / 2 - thickness

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: Theme.alpha(root.accent, 0.13); strokeWidth: root.thickness; fillColor: "transparent"
            PathAngleArc { centerX: root.width / 2; centerY: root.height / 2; radiusX: root.r; radiusY: root.r; startAngle: 135; sweepAngle: 270 }
        }
        ShapePath {
            strokeColor: root.accent; strokeWidth: root.thickness; fillColor: "transparent"; capStyle: ShapePath.RoundCap
            PathAngleArc { centerX: root.width / 2; centerY: root.height / 2; radiusX: root.r; radiusY: root.r; startAngle: 135; sweepAngle: Math.max(0.5, 270 * root.shown) }
        }
        ShapePath {
            strokeColor: Theme.alpha(root.accent, 0.35); strokeWidth: 1; fillColor: "transparent"
            PathAngleArc { centerX: root.width / 2; centerY: root.height / 2; radiusX: root.r - 9; radiusY: root.r - 9; startAngle: 0; sweepAngle: 360 }
        }
    }
    Column {
        anchors.centerIn: parent
        spacing: 0
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: Math.round(root.shown * 100) + "%"
            color: Theme.text
            font.family: Theme.mono; font.pixelSize: Math.max(12, root.width * 0.19); font.bold: true
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.label
            color: Theme.muted
            font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1.5
        }
    }
}
