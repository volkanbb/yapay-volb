import QtQuick
import QtQuick.Shapes

// Two expressive eyes with procedural eyelids, glowing cyan irises and feather brows.
Item {
    id: root
    width: 400; height: 500

    property real lookX: 0          // -1..1
    property real lookY: 0          // -1..1
    property real lidLeft: 0.35     // 0 = wide open, 1 = closed
    property real lidRight: 0.35
    property real blink: 0          // 0..1 overrides lids while blinking
    property real tiltLeft: 6       // eye slant in degrees
    property real tiltRight: -6
    property real browLeftAngle: -4
    property real browRightAngle: 4
    property real browLeftLift: 0
    property real browRightLift: 0
    property real glow: 0.6
    property real pupilScale: 1.0
    property color irisColor: Theme.cyan
    property color lidColor: "#E9BD45"

    component Eye: Item {
        id: eye
        property real cx: 0
        property real cy: 0
        property real a: 21
        property real b: 24
        property real lid: 0.35
        property real tilt: 0
        property real browAngle: 0
        property real browLift: 0
        property bool mirrored: false

        readonly property real lidC: Math.max(0.03, Math.min(0.97, lid))
        readonly property real y0: cy - b + lidC * 2 * b
        readonly property real dy: (y0 - cy) / b
        readonly property real dx: a * Math.sqrt(Math.max(0, 1 - dy * dy))
        readonly property real px: cx + Math.max(-1, Math.min(1, root.lookX)) * 7
        readonly property real py: cy + Math.max(-1, Math.min(1, root.lookY)) * 6 + 2

        anchors.fill: parent
        transform: Rotation { origin.x: eye.cx; origin.y: eye.cy; angle: eye.tilt }

        // glow halo
        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: "transparent"
                fillGradient: RadialGradient {
                    centerX: eye.cx; centerY: eye.cy; centerRadius: 44; focalX: eye.cx; focalY: eye.cy
                    GradientStop { position: 0.45; color: Theme.alpha(root.irisColor, 0.42 * root.glow) }
                    GradientStop { position: 1.0; color: Theme.alpha(root.irisColor, 0) }
                }
                startX: eye.cx - 44; startY: eye.cy
                PathArc { x: eye.cx + 44; y: eye.cy; radiusX: 44; radiusY: 44 }
                PathArc { x: eye.cx - 44; y: eye.cy; radiusX: 44; radiusY: 44 }
            }
        }
        // sclera
        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: "#2A1C05"; strokeWidth: 2.4
                fillGradient: RadialGradient {
                    centerX: eye.cx - 4; centerY: eye.cy - 6; centerRadius: eye.b * 1.3; focalX: eye.cx - 4; focalY: eye.cy - 6
                    GradientStop { position: 0; color: "#FFFFFF" }
                    GradientStop { position: 1; color: "#C9D8E6" }
                }
                startX: eye.cx - eye.a; startY: eye.cy
                PathArc { x: eye.cx + eye.a; y: eye.cy; radiusX: eye.a; radiusY: eye.b }
                PathArc { x: eye.cx - eye.a; y: eye.cy; radiusX: eye.a; radiusY: eye.b }
            }
        }
        // iris + pupil
        Rectangle {
            readonly property real r: 12.5
            x: eye.px - r; y: eye.py - r; width: r * 2; height: r * 2; radius: r
            color: "#0B1C2E"
            border.width: 2.6
            border.color: root.irisColor
            Rectangle {
                anchors.centerIn: parent
                width: 12 * root.pupilScale; height: width; radius: width / 2
                color: "#02060B"
            }
            Rectangle {   // inner iris glow ring
                anchors.centerIn: parent
                width: 18; height: 18; radius: 9
                color: "transparent"
                border.width: 1
                border.color: Theme.alpha(root.irisColor, 0.5)
            }
            Rectangle { x: 5; y: 4; width: 6; height: 6; radius: 3; color: "white"; opacity: 0.95 }
            Rectangle { x: 15; y: 15; width: 2.5; height: 2.5; radius: 1.25; color: "white"; opacity: 0.7 }
        }
        // eyelid
        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: "transparent"
                fillGradient: LinearGradient {
                    x1: 0; y1: eye.cy - eye.b; x2: 0; y2: eye.cy + eye.b * 0.4
                    GradientStop { position: 0; color: Qt.darker(root.lidColor, 2.4) }
                    GradientStop { position: 1; color: root.lidColor }
                }
                startX: eye.cx - eye.dx; startY: eye.y0
                PathArc {
                    x: eye.cx + eye.dx; y: eye.y0
                    radiusX: eye.a; radiusY: eye.b
                    useLargeArc: eye.y0 > eye.cy
                    direction: PathArc.Clockwise
                }
                PathQuad { controlX: eye.cx; controlY: eye.y0 + 5; x: eye.cx - eye.dx; y: eye.y0 }
            }
            ShapePath {   // lid line
                strokeColor: "#2A1C05"; strokeWidth: 3.2; fillColor: "transparent"; capStyle: ShapePath.RoundCap
                startX: eye.cx - eye.dx - 2; startY: eye.y0
                PathQuad { controlX: eye.cx; controlY: eye.y0 + 5; x: eye.cx + eye.dx + 2; y: eye.y0 }
            }
        }
        // feather brow
        Rectangle {
            width: 38; height: 8; radius: 4
            x: eye.cx - width / 2 + (eye.mirrored ? 3 : -3)
            y: eye.cy - eye.b - 16 - eye.browLift
            rotation: eye.browAngle
            gradient: Gradient {
                GradientStop { position: 0; color: "#8A6A1E" }
                GradientStop { position: 1; color: "#3E2C08" }
            }
        }
    }

    Eye {
        cx: 163; cy: 236
        lid: Math.max(root.lidLeft, root.blink)
        tilt: root.tiltLeft
        browAngle: root.browLeftAngle
        browLift: root.browLeftLift
    }
    Eye {
        cx: 237; cy: 236
        lid: Math.max(root.lidRight, root.blink)
        tilt: root.tiltRight
        browAngle: root.browRightAngle
        browLift: root.browRightLift
        mirrored: true
    }
}
