import QtQuick
import QtQuick.Shapes

// VOLB's oversized hoodie. Drawn in a 400x500 design space.
// `part` selects the layer so the hood can sit behind / in front of the head:
//   "body"   – torso, sleeves, pocket, chest emblem
//   "back"   – the hood behind the head + dark inner opening
//   "shadow" – the shadow the hood casts on the top of the face
//   "rim"    – the hood's front edge (covers the head outline)
//   "strings"– drawstrings with glowing aglets
Item {
    id: root
    width: 400; height: 500
    property string part: "body"
    property color accent: Theme.cyan
    property real sway: 0          // -1..1, drawstring swing
    property real breathe: 0       // -1..1
    property real glow: 0.6        // emblem / trim glow
    property color fabricTop: "#1E2530"
    property color fabricBottom: "#0A0D12"

    // ---------------------------------------------------------------- torso
    Item {
        anchors.fill: parent
        visible: root.part === "body"
        transform: Scale { origin.x: 200; origin.y: 500; yScale: 1 + root.breathe * 0.010; xScale: 1 - root.breathe * 0.004 }

        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: Theme.alpha(root.accent, 0.28)
                strokeWidth: 1.5
                fillGradient: LinearGradient {
                    x1: 200; y1: 330; x2: 200; y2: 500
                    GradientStop { position: 0; color: root.fabricTop }
                    GradientStop { position: 1; color: root.fabricBottom }
                }
                startX: 108; startY: 342
                PathCubic { control1X: 52; control1Y: 352; control2X: 22; control2Y: 405; x: 14; y: 500 }
                PathLine { x: 386; y: 500 }
                PathCubic { control1X: 378; control1Y: 405; control2X: 348; control2Y: 352; x: 292; y: 342 }
                PathLine { x: 108; y: 342 }
            }
        }
        // sleeve seams + shoulder light
        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: "#2C3644"; strokeWidth: 2; fillColor: "transparent"; capStyle: ShapePath.RoundCap
                startX: 84; startY: 362
                PathQuad { controlX: 66; controlY: 420; x: 70; y: 500 }
            }
            ShapePath {
                strokeColor: "#2C3644"; strokeWidth: 2; fillColor: "transparent"; capStyle: ShapePath.RoundCap
                startX: 316; startY: 362
                PathQuad { controlX: 334; controlY: 420; x: 330; y: 500 }
            }
            ShapePath {   // rim light on the right shoulder
                strokeColor: Theme.alpha(root.accent, 0.45 * root.glow); strokeWidth: 2.5; fillColor: "transparent"
                capStyle: ShapePath.RoundCap
                startX: 300; startY: 346
                PathCubic { control1X: 345; control1Y: 356; control2X: 370; control2Y: 400; x: 378; y: 455 }
            }
            // kangaroo pocket
            ShapePath {
                strokeColor: "#2C3644"; strokeWidth: 2
                fillColor: Qt.rgba(1, 1, 1, 0.025)
                joinStyle: ShapePath.RoundJoin
                startX: 128; startY: 500
                PathLine { x: 142; y: 446 }
                PathQuad { controlX: 200; controlY: 438; x: 258; y: 446 }
                PathLine { x: 272; y: 500 }
            }
        }
        // chest emblem: glowing V chevron
        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: Theme.alpha(root.accent, 0.18 * root.glow); strokeWidth: 10
                fillColor: "transparent"; capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
                startX: 184; startY: 392
                PathLine { x: 200; y: 416 }
                PathLine { x: 216; y: 392 }
            }
            ShapePath {
                strokeColor: root.accent; strokeWidth: 3
                fillColor: "transparent"; capStyle: ShapePath.RoundCap; joinStyle: ShapePath.RoundJoin
                startX: 184; startY: 392
                PathLine { x: 200; y: 416 }
                PathLine { x: 216; y: 392 }
            }
        }
        Text {
            x: 176; y: 420; width: 48
            horizontalAlignment: Text.AlignHCenter
            text: "V0LB"
            font.family: Theme.mono; font.pixelSize: 8; font.letterSpacing: 2
            color: Theme.alpha(root.accent, 0.55)
        }
    }

    // ---------------------------------------------------------------- hood (behind head)
    Shape {
        anchors.fill: parent
        visible: root.part === "back"
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: Theme.alpha(root.accent, 0.22); strokeWidth: 1.5
            fillGradient: LinearGradient {
                x1: 120; y1: 60; x2: 280; y2: 352
                GradientStop { position: 0; color: "#29313D" }
                GradientStop { position: 0.55; color: "#161C25" }
                GradientStop { position: 1; color: "#0C1016" }
            }
            startX: 200; startY: 58
            PathCubic { control1X: 304; control1Y: 56; control2X: 356; control2Y: 150; x: 349; y: 246 }
            PathCubic { control1X: 344; control1Y: 302; control2X: 318; control2Y: 338; x: 292; y: 354 }
            PathLine { x: 108; y: 354 }
            PathCubic { control1X: 82; control1Y: 338; control2X: 56; control2Y: 302; x: 51; y: 246 }
            PathCubic { control1X: 44; control1Y: 150; control2X: 96; control2Y: 56; x: 200; y: 58 }
        }
        // hood fold / center seam
        ShapePath {
            strokeColor: "#323C4A"; strokeWidth: 2; fillColor: "transparent"; capStyle: ShapePath.RoundCap
            startX: 200; startY: 62
            PathQuad { controlX: 206; controlY: 84; x: 202; y: 104 }
        }
        // dark opening where the face sits
        ShapePath {
            strokeColor: "transparent"
            fillGradient: RadialGradient {
                centerX: 200; centerY: 250; centerRadius: 150; focalX: 200; focalY: 270
                GradientStop { position: 0; color: "#0A0E14" }
                GradientStop { position: 1; color: "#020305" }
            }
            startX: 200; startY: 106
            PathCubic { control1X: 270; control1Y: 106; control2X: 307; control2Y: 165; x: 304; y: 240 }
            PathCubic { control1X: 302; control1Y: 302; control2X: 264; control2Y: 342; x: 200; y: 344 }
            PathCubic { control1X: 136; control1Y: 342; control2X: 98; control2Y: 302; x: 96; y: 240 }
            PathCubic { control1X: 93; control1Y: 165; control2X: 130; control2Y: 106; x: 200; y: 106 }
        }
    }

    // ---------------------------------------------------------------- shadow on the face
    Shape {
        anchors.fill: parent
        visible: root.part === "shadow"
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: "transparent"
            fillGradient: LinearGradient {
                x1: 200; y1: 106; x2: 200; y2: 232
                GradientStop { position: 0; color: Qt.rgba(0.01, 0.015, 0.025, 0.96) }
                GradientStop { position: 0.55; color: Qt.rgba(0.01, 0.015, 0.025, 0.55) }
                GradientStop { position: 1; color: Qt.rgba(0.01, 0.015, 0.025, 0.0) }
            }
            startX: 200; startY: 106
            PathCubic { control1X: 270; control1Y: 106; control2X: 307; control2Y: 165; x: 304; y: 240 }
            PathCubic { control1X: 302; control1Y: 302; control2X: 264; control2Y: 342; x: 200; y: 344 }
            PathCubic { control1X: 136; control1Y: 342; control2X: 98; control2Y: 302; x: 96; y: 240 }
            PathCubic { control1X: 93; control1Y: 165; control2X: 130; control2Y: 106; x: 200; y: 106 }
        }
        // side shadows (hood walls)
        ShapePath {
            strokeColor: "transparent"
            fillGradient: LinearGradient {
                x1: 96; y1: 0; x2: 304; y2: 0
                GradientStop { position: 0; color: Qt.rgba(0, 0, 0, 0.55) }
                GradientStop { position: 0.2; color: Qt.rgba(0, 0, 0, 0.0) }
                GradientStop { position: 0.8; color: Qt.rgba(0, 0, 0, 0.0) }
                GradientStop { position: 1; color: Qt.rgba(0, 0, 0, 0.5) }
            }
            startX: 200; startY: 106
            PathCubic { control1X: 270; control1Y: 106; control2X: 307; control2Y: 165; x: 304; y: 240 }
            PathCubic { control1X: 302; control1Y: 302; control2X: 264; control2Y: 342; x: 200; y: 344 }
            PathCubic { control1X: 136; control1Y: 342; control2X: 98; control2Y: 302; x: 96; y: 240 }
            PathCubic { control1X: 93; control1Y: 165; control2X: 130; control2Y: 106; x: 200; y: 106 }
        }
    }

    // ---------------------------------------------------------------- hood front rim
    Shape {
        anchors.fill: parent
        visible: root.part === "rim"
        preferredRendererType: Shape.CurveRenderer
        ShapePath {
            strokeColor: "#283140"; strokeWidth: 15; fillColor: "transparent"; joinStyle: ShapePath.RoundJoin
            startX: 200; startY: 106
            PathCubic { control1X: 270; control1Y: 106; control2X: 307; control2Y: 165; x: 304; y: 240 }
            PathCubic { control1X: 302; control1Y: 302; control2X: 264; control2Y: 342; x: 200; y: 344 }
            PathCubic { control1X: 136; control1Y: 342; control2X: 98; control2Y: 302; x: 96; y: 240 }
            PathCubic { control1X: 93; control1Y: 165; control2X: 130; control2Y: 106; x: 200; y: 106 }
        }
        ShapePath {   // stitched highlight
            strokeColor: "#3A4555"; strokeWidth: 2; fillColor: "transparent"
            startX: 200; startY: 99
            PathCubic { control1X: 275; control1Y: 99; control2X: 314; control2Y: 162; x: 311; y: 240 }
            PathCubic { control1X: 309; control1Y: 306; control2X: 268; control2Y: 349; x: 200; y: 351 }
            PathCubic { control1X: 132; control1Y: 349; control2X: 91; control2Y: 306; x: 89; y: 240 }
            PathCubic { control1X: 86; control1Y: 162; control2X: 125; control2Y: 99; x: 200; y: 99 }
        }
        ShapePath {   // inner holographic trim
            strokeColor: Theme.alpha(root.accent, 0.55 * root.glow); strokeWidth: 1.5; fillColor: "transparent"
            startX: 200; startY: 113
            PathCubic { control1X: 265; control1Y: 113; control2X: 300; control2Y: 168; x: 297; y: 240 }
            PathCubic { control1X: 295; control1Y: 298; control2X: 260; control2Y: 335; x: 200; y: 337 }
            PathCubic { control1X: 140; control1Y: 335; control2X: 105; control2Y: 298; x: 103; y: 240 }
            PathCubic { control1X: 100; control1Y: 168; control2X: 135; control2Y: 113; x: 200; y: 113 }
        }
    }

    // ---------------------------------------------------------------- drawstrings
    Item {
        anchors.fill: parent
        visible: root.part === "strings"
        Shape {
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeColor: "#C9D6E3"; strokeWidth: 3.2; fillColor: "transparent"; capStyle: ShapePath.RoundCap
                startX: 176; startY: 346
                PathQuad { controlX: 170 + root.sway * 4; controlY: 382; x: 168 + root.sway * 7; y: 418 }
            }
            ShapePath {
                strokeColor: "#C9D6E3"; strokeWidth: 3.2; fillColor: "transparent"; capStyle: ShapePath.RoundCap
                startX: 224; startY: 346
                PathQuad { controlX: 230 + root.sway * 4; controlY: 384; x: 232 + root.sway * 7; y: 422 }
            }
        }
        Repeater {
            model: [Qt.point(168, 418), Qt.point(232, 422)]
            Rectangle {
                width: 7; height: 14; radius: 2
                x: modelData.x + root.sway * 7 - width / 2
                y: modelData.y - 2
                color: root.accent
                opacity: 0.6 + 0.4 * root.glow
                Rectangle { anchors.centerIn: parent; width: 16; height: 22; radius: 8; color: Theme.alpha(root.accent, 0.18) }
            }
        }
        // eyelets
        Repeater {
            model: [Qt.point(176, 346), Qt.point(224, 346)]
            Rectangle {
                width: 9; height: 9; radius: 4.5
                x: modelData.x - 4.5; y: modelData.y - 4.5
                color: "#0B0F15"; border.color: "#7C8A99"; border.width: 1.5
            }
        }
    }
}
