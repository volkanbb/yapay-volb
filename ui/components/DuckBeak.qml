import QtQuick
import QtQuick.Shapes

// Wide orange duck bill. `open` (0..1) drives the lower mandible for speech.
Item {
    id: root
    width: 400; height: 500
    property real open: 0
    property real smirk: 0          // -1..1 subtle asymmetric tilt
    property color upper: "#FF9A2E"
    property color upperShade: "#E2600E"
    property color lower: "#E8650F"
    property color lowerShade: "#A9420A"

    readonly property real o: Math.max(0, Math.min(1, open))
    readonly property real drop: o * 20

    transform: Rotation { origin.x: 200; origin.y: 282; angle: root.smirk * 4 }

    // mouth interior
    Shape {
        anchors.fill: parent
        visible: root.o > 0.02
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: "transparent"
            fillColor: "#2B0805"
            startX: 160; startY: 292
            PathQuad { controlX: 200; controlY: 300; x: 240; y: 292 }
            PathCubic { control1X: 238; control1Y: 300 + root.drop; control2X: 222; control2Y: 306 + root.drop; x: 200; y: 306 + root.drop }
            PathCubic { control1X: 178; control1Y: 306 + root.drop; control2X: 162; control2Y: 300 + root.drop; x: 160; y: 292 }
        }
        ShapePath {   // tongue
            strokeColor: "transparent"
            fillColor: "#C2414B"
            startX: 182; startY: 302 + root.drop
            PathQuad { controlX: 200; controlY: 292 + root.drop * 0.6; x: 218; y: 302 + root.drop }
            PathQuad { controlX: 200; controlY: 308 + root.drop; x: 182; y: 302 + root.drop }
        }
    }

    // lower mandible
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        transform: Translate { y: root.drop }
        ShapePath {
            strokeColor: "#5E2405"; strokeWidth: 1.6
            fillGradient: LinearGradient {
                x1: 200; y1: 292; x2: 200; y2: 318
                GradientStop { position: 0; color: root.lower }
                GradientStop { position: 1; color: root.lowerShade }
            }
            startX: 158; startY: 293
            PathCubic { control1X: 172; control1Y: 302; control2X: 228; control2Y: 302; x: 242; y: 293 }
            PathCubic { control1X: 240; control1Y: 310; control2X: 222; control2Y: 318; x: 200; y: 318 }
            PathCubic { control1X: 178; control1Y: 318; control2X: 160; control2Y: 310; x: 158; y: 293 }
        }
    }

    // upper bill
    Shape {
        anchors.fill: parent
        preferredRendererType: Shape.CurveRenderer
        transform: Translate { y: -root.o * 2 }
        ShapePath {
            strokeColor: "#6A2A04"; strokeWidth: 1.8
            fillGradient: LinearGradient {
                x1: 200; y1: 258; x2: 200; y2: 300
                GradientStop { position: 0; color: root.upper }
                GradientStop { position: 1; color: root.upperShade }
            }
            startX: 146; startY: 279
            PathCubic { control1X: 147; control1Y: 263; control2X: 172; control2Y: 257; x: 200; y: 257 }
            PathCubic { control1X: 228; control1Y: 257; control2X: 253; control2Y: 263; x: 254; y: 279 }
            PathCubic { control1X: 255; control1Y: 293; control2X: 233; control2Y: 300; x: 200; y: 298 }
            PathCubic { control1X: 167; control1Y: 300; control2X: 145; control2Y: 293; x: 146; y: 279 }
        }
        ShapePath {   // highlight
            strokeColor: "transparent"
            fillColor: Qt.rgba(1, 1, 1, 0.28)
            startX: 166; startY: 268
            PathQuad { controlX: 190; controlY: 260; x: 214; y: 263 }
            PathQuad { controlX: 190; controlY: 268; x: 166; y: 268 }
        }
        ShapePath {   // nostrils
            strokeColor: "transparent"; fillColor: "#8A3306"
            startX: 184; startY: 274
            PathArc { x: 192; y: 274; radiusX: 4; radiusY: 2.4 }
            PathArc { x: 184; y: 274; radiusX: 4; radiusY: 2.4 }
        }
        ShapePath {
            strokeColor: "transparent"; fillColor: "#8A3306"
            startX: 208; startY: 274
            PathArc { x: 216; y: 274; radiusX: 4; radiusY: 2.4 }
            PathArc { x: 208; y: 274; radiusX: 4; radiusY: 2.4 }
        }
    }
}
