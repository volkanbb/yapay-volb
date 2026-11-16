import QtQuick
import QtQuick.Shapes

// VOLB's head: a warm golden duck head with soft shading and a holographic rim light.
Item {
    id: root
    width: 400; height: 500
    property color base: "#F2C64B"
    property color shade: "#B9831A"
    property color accent: Theme.cyan
    property real rimLight: 0.6
    property real flush: 0          // 0..1 red tint for error state

    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        // head
        ShapePath {
            strokeColor: "#5A3C08"; strokeWidth: 1.5
            fillGradient: RadialGradient {
                centerX: 178; centerY: 205; centerRadius: 135; focalX: 170; focalY: 195
                GradientStop { position: 0.0; color: Qt.lighter(root.base, 1.08) }
                GradientStop { position: 0.6; color: root.base }
                GradientStop { position: 1.0; color: root.shade }
            }
            startX: 200; startY: 136
            PathCubic { control1X: 262; control1Y: 136; control2X: 302; control2Y: 182; x: 302; y: 240 }
            PathCubic { control1X: 302; control1Y: 296; control2X: 258; control2Y: 340; x: 200; y: 340 }
            PathCubic { control1X: 142; control1Y: 340; control2X: 98; control2Y: 296; x: 98; y: 240 }
            PathCubic { control1X: 98; control1Y: 182; control2X: 138; control2Y: 136; x: 200; y: 136 }
        }
        // cheek fluff / jaw shading
        ShapePath {
            strokeColor: "transparent"
            fillGradient: LinearGradient {
                x1: 200; y1: 270; x2: 200; y2: 340
                GradientStop { position: 0; color: Qt.rgba(0.45, 0.28, 0.02, 0.0) }
                GradientStop { position: 1; color: Qt.rgba(0.45, 0.28, 0.02, 0.35) }
            }
            startX: 104; startY: 270
            PathQuad { controlX: 200; controlY: 300; x: 296; y: 270 }
            PathCubic { control1X: 285; control1Y: 318; control2X: 248; control2Y: 340; x: 200; y: 340 }
            PathCubic { control1X: 152; control1Y: 340; control2X: 115; control2Y: 318; x: 104; y: 270 }
        }
        // holographic rim light (right side)
        ShapePath {
            strokeColor: Theme.alpha(root.accent, 0.55 * root.rimLight); strokeWidth: 3
            fillColor: "transparent"; capStyle: ShapePath.RoundCap
            startX: 268; startY: 175
            PathCubic { control1X: 292; control1Y: 200; control2X: 300; control2Y: 245; x: 288; y: 286 }
        }
        // error flush
        ShapePath {
            strokeColor: "transparent"
            fillColor: Qt.rgba(1, 0.2, 0.3, 0.22 * root.flush)
            startX: 200; startY: 136
            PathCubic { control1X: 262; control1Y: 136; control2X: 302; control2Y: 182; x: 302; y: 240 }
            PathCubic { control1X: 302; control1Y: 296; control2X: 258; control2Y: 340; x: 200; y: 340 }
            PathCubic { control1X: 142; control1Y: 340; control2X: 98; control2Y: 296; x: 98; y: 240 }
            PathCubic { control1X: 98; control1Y: 182; control2X: 138; control2Y: 136; x: 200; y: 136 }
        }
    }

    // feather tufts poking out under the hood
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: "#6B4A0C"; strokeWidth: 1.2
            fillColor: Qt.darker(root.base, 1.35)
            startX: 178; startY: 150
            PathQuad { controlX: 186; controlY: 168; x: 196; y: 176 }
            PathQuad { controlX: 198; controlY: 160; x: 206; y: 148 }
            PathQuad { controlX: 214; controlY: 166; x: 222; y: 172 }
            PathQuad { controlX: 226; controlY: 156; x: 232; y: 146 }
            PathQuad { controlX: 205; controlY: 136; x: 178; y: 150 }
        }
    }
}
