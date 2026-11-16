import QtQuick
import QtQuick.Shapes

// VOLB — a hoodie-wearing duck built entirely from vector shapes and procedural animation.
// States: idle | listening | thinking | speaking | working | error
Item {
    id: root
    property string mood: "idle"
    property real micLevel: 0
    property real speechLevel: 0
    property bool showFx: true
    property bool compact: false     // small avatar mode (fewer effects)

    // ------------------------------------------------------------------ time base
    property real t: 0
    FrameAnimation { running: root.visible; onTriggered: root.t += Math.min(frameTime, 0.05) }

    readonly property bool isIdle: mood === "idle"
    readonly property bool isListening: mood === "listening"
    readonly property bool isThinking: mood === "thinking"
    readonly property bool isSpeaking: mood === "speaking"
    readonly property bool isWorking: mood === "working"
    readonly property bool isError: mood === "error"

    readonly property color accent: isError ? Theme.red : isWorking ? Qt.rgba(0.0, 0.85, 1.0, 1) : isThinking ? "#3D8BFF" : Theme.cyan

    // ------------------------------------------------------------------ smoothed audio
    property real micS: 0
    property real speechS: 0
    FrameAnimation {
        running: root.visible
        onTriggered: {
            root.micS += (root.micLevel - root.micS) * Math.min(1, frameTime * 12)
            root.speechS += (root.speechLevel - root.speechS) * Math.min(1, frameTime * 20)
        }
    }

    // ------------------------------------------------------------------ expression targets
    property real lidL: isListening ? 0.10 : isThinking ? 0.30 : isWorking ? 0.48 : isError ? 0.12 : isSpeaking ? 0.24 : 0.38
    property real lidR: isListening ? 0.10 : isThinking ? 0.36 : isWorking ? 0.48 : isError ? 0.46 : isSpeaking ? 0.24 : 0.38
    property real browLA: isListening ? -8 : isThinking ? 4 : isWorking ? 12 : isError ? -16 : isSpeaking ? -5 : 3
    property real browRA: isListening ? 8 : isThinking ? -14 : isWorking ? -12 : isError ? 18 : isSpeaking ? 5 : -3
    property real browLL: isListening ? 5 : isThinking ? 2 : isWorking ? -3 : isError ? 8 : 1
    property real browRL: isListening ? 5 : isThinking ? 7 : isWorking ? -3 : isError ? -2 : 1
    property real eyeTilt: isWorking ? 9 : isError ? 0 : isListening ? 2 : 6
    property real tiltTarget: isListening ? 5 : isError ? -9 : isWorking ? 2 : isThinking ? -3 : 0
    property real glowTarget: isListening ? 1.0 : isThinking ? 0.85 : isWorking ? 0.9 : isSpeaking ? 0.8 : isError ? 0.5 : 0.55
    property real smirkTarget: isError ? -1 : isIdle ? 0.6 : 0.2

    Behavior on lidL { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
    Behavior on lidR { NumberAnimation { duration: 260; easing.type: Easing.OutCubic } }
    Behavior on browLA { NumberAnimation { duration: 300; easing.type: Easing.OutBack } }
    Behavior on browRA { NumberAnimation { duration: 300; easing.type: Easing.OutBack } }
    Behavior on browLL { NumberAnimation { duration: 300 } }
    Behavior on browRL { NumberAnimation { duration: 300 } }
    Behavior on eyeTilt { NumberAnimation { duration: 400 } }
    Behavior on tiltTarget { NumberAnimation { duration: 600; easing.type: Easing.InOutQuad } }
    Behavior on glowTarget { NumberAnimation { duration: 500 } }
    Behavior on smirkTarget { NumberAnimation { duration: 400 } }

    // ------------------------------------------------------------------ blinking
    property real blink: 0
    SequentialAnimation {
        id: blinkAnim
        NumberAnimation { target: root; property: "blink"; to: 1; duration: 70; easing.type: Easing.InQuad }
        NumberAnimation { target: root; property: "blink"; to: 0; duration: 110; easing.type: Easing.OutQuad }
    }
    Timer {
        id: blinkTimer
        running: root.visible
        interval: 3000
        onTriggered: {
            blinkAnim.restart()
            if (Math.random() < 0.18) doubleBlink.start()
            interval = 2200 + Math.random() * 4200
        }
    }
    Timer { id: doubleBlink; interval: 260; onTriggered: blinkAnim.restart() }

    // ------------------------------------------------------------------ gaze
    property real idleLookX: 0
    property real idleLookY: 0
    Timer {
        running: root.visible && (root.isIdle || root.isSpeaking)
        interval: 1800; repeat: true
        onTriggered: {
            interval = 1200 + Math.random() * 2800
            if (Math.random() < 0.4) { root.idleLookX = 0; root.idleLookY = 0.2 }
            else { root.idleLookX = Math.random() * 1.6 - 0.8; root.idleLookY = Math.random() * 1.0 - 0.4 }
        }
    }
    readonly property real lookXTarget: isThinking ? 0.55 * Math.sin(t * 2.4) + 0.2
                                       : isWorking ? 0.45 * Math.sin(t * 1.3)
                                       : isListening ? 0 : isError ? -0.3 + 0.25 * Math.sin(t * 5) : idleLookX
    readonly property real lookYTarget: isThinking ? -0.75 : isWorking ? 0.6 : isListening ? 0.15 : isError ? -0.2 : idleLookY
    property real lookX: 0
    property real lookY: 0
    FrameAnimation {
        running: root.visible
        onTriggered: {
            const k = Math.min(1, frameTime * (root.isThinking ? 6 : 9))
            root.lookX += (root.lookXTarget - root.lookX) * k
            root.lookY += (root.lookYTarget - root.lookY) * k
        }
    }

    // ------------------------------------------------------------------ mouth
    readonly property real fakeTalk: Math.max(0, Math.sin(t * 13.0) * 0.55 + Math.sin(t * 7.3) * 0.35 + 0.15) * (0.6 + 0.4 * Math.abs(Math.sin(t * 2.2)))
    readonly property real mouthOpen: isSpeaking ? Math.min(1, (speechS > 0.03 ? speechS * 1.25 : fakeTalk)) : isError ? 0.12 : 0

    // ------------------------------------------------------------------ motion
    readonly property real floatAmp: isListening ? 4 : isWorking ? 3 : isThinking ? 5 : 7
    readonly property real floatY: Math.sin(t * (isThinking ? 1.8 : 1.15)) * floatAmp
    readonly property real headTilt: tiltTarget + Math.sin(t * 0.9) * (isIdle ? 2.2 : 1.0) + (isSpeaking ? Math.sin(t * 3.1) * 1.5 : 0)
    readonly property real headNod: (isSpeaking ? mouthOpen * 3 : 0) + (isListening ? micS * 6 : 0) + (isWorking ? 3 : 0)
    readonly property real breathe: Math.sin(t * 1.6)
    readonly property real sway: Math.sin(t * 1.15 - 0.8) * 0.8

    property real glitch: 0
    Timer {
        running: root.isError && root.visible
        interval: 900; repeat: true
        onTriggered: { glitchAnim.restart(); interval = 600 + Math.random() * 1600 }
    }
    SequentialAnimation {
        id: glitchAnim
        NumberAnimation { target: root; property: "glitch"; to: 5; duration: 40 }
        NumberAnimation { target: root; property: "glitch"; to: -4; duration: 40 }
        NumberAnimation { target: root; property: "glitch"; to: 0; duration: 60 }
    }

    // ------------------------------------------------------------------ rig (400x500 design space)
    Item {
        id: rig
        width: 400; height: 500
        anchors.centerIn: parent
        scale: Math.min(root.width / 470, root.height / 560)

        // aura
        Shape {
            x: -100; y: -60; width: 600; height: 620
            preferredRendererType: Shape.CurveRenderer
            opacity: 0.7 + 0.3 * Math.sin(root.t * 1.4)
            ShapePath {
                strokeColor: "transparent"
                fillGradient: RadialGradient {
                    centerX: 300; centerY: 290; centerRadius: 290; focalX: 300; focalY: 290
                    GradientStop { position: 0.0; color: Theme.alpha(root.accent, 0.20 * root.glowTarget) }
                    GradientStop { position: 0.5; color: Theme.alpha(root.accent, 0.06 * root.glowTarget) }
                    GradientStop { position: 1.0; color: Theme.alpha(root.accent, 0) }
                }
                startX: 10; startY: 290
                PathArc { x: 590; y: 290; radiusX: 290; radiusY: 290 }
                PathArc { x: 10; y: 290; radiusX: 290; radiusY: 290 }
            }
        }

        // holographic projector base
        Item {
            id: base
            visible: !root.compact
            x: 0; y: 470; width: 400; height: 70
            Shape {
                anchors.fill: parent
                preferredRendererType: Shape.CurveRenderer
                ShapePath {
                    strokeColor: Theme.alpha(root.accent, 0.55); strokeWidth: 2
                    fillGradient: RadialGradient {
                        centerX: 200; centerY: 35; centerRadius: 190; focalX: 200; focalY: 35
                        GradientStop { position: 0; color: Theme.alpha(root.accent, 0.22) }
                        GradientStop { position: 1; color: Theme.alpha(root.accent, 0.0) }
                    }
                    startX: 20; startY: 35
                    PathArc { x: 380; y: 35; radiusX: 180; radiusY: 26 }
                    PathArc { x: 20; y: 35; radiusX: 180; radiusY: 26 }
                }
                ShapePath {
                    strokeColor: Theme.alpha(root.accent, 0.3); strokeWidth: 1; fillColor: "transparent"
                    startX: 60; startY: 35
                    PathArc { x: 340; y: 35; radiusX: 140; radiusY: 18 }
                    PathArc { x: 60; y: 35; radiusX: 140; radiusY: 18 }
                }
            }
            Repeater {
                model: 24
                Rectangle {
                    readonly property real ang: index / 24 * Math.PI * 2 + root.t * 0.35
                    width: 3; height: 3; radius: 1.5
                    x: 200 + Math.cos(ang) * 180 - 1.5
                    y: 35 + Math.sin(ang) * 26 - 1.5
                    color: root.accent
                    opacity: 0.25 + 0.75 * (Math.sin(ang) * 0.5 + 0.5)
                }
            }
        }

        // processing ring (thinking / working)
        Item {
            id: procRing
            visible: opacity > 0.01 && root.showFx
            opacity: root.isThinking ? 1 : root.isWorking ? 0.45 : 0
            Behavior on opacity { NumberAnimation { duration: 400 } }
            x: 0; y: 0; width: 400; height: 500
            Shape {
                anchors.fill: parent
                preferredRendererType: Shape.CurveRenderer
                rotation: root.t * 70
                transformOrigin: Item.Center
                ShapePath {
                    strokeColor: root.accent; strokeWidth: 3; fillColor: "transparent"; capStyle: ShapePath.RoundCap
                    PathAngleArc { centerX: 200; centerY: 250; radiusX: 172; radiusY: 172; startAngle: 0; sweepAngle: 70 }
                }
                ShapePath {
                    strokeColor: root.accent; strokeWidth: 3; fillColor: "transparent"; capStyle: ShapePath.RoundCap
                    PathAngleArc { centerX: 200; centerY: 250; radiusX: 172; radiusY: 172; startAngle: 180; sweepAngle: 70 }
                }
            }
            Shape {
                anchors.fill: parent
                preferredRendererType: Shape.CurveRenderer
                rotation: -root.t * 45
                transformOrigin: Item.Center
                ShapePath {
                    strokeColor: Theme.alpha(Theme.blue, 0.9); strokeWidth: 1.5; fillColor: "transparent"
                    PathAngleArc { centerX: 200; centerY: 250; radiusX: 186; radiusY: 186; startAngle: 30; sweepAngle: 120 }
                }
                ShapePath {
                    strokeColor: Theme.alpha(Theme.blue, 0.9); strokeWidth: 1.5; fillColor: "transparent"
                    PathAngleArc { centerX: 200; centerY: 250; radiusX: 186; radiusY: 186; startAngle: 210; sweepAngle: 120 }
                }
            }
            Repeater {   // tick marks
                model: 60
                Rectangle {
                    readonly property real ang: index / 60 * Math.PI * 2 + root.t * 0.25
                    width: index % 5 === 0 ? 8 : 4; height: 1.5
                    x: 200 + Math.cos(ang) * 160 - width / 2
                    y: 250 + Math.sin(ang) * 160
                    rotation: ang * 180 / Math.PI
                    color: Theme.alpha(root.accent, index % 5 === 0 ? 0.8 : 0.35)
                }
            }
        }

        // listening sound waves
        Repeater {
            model: 4
            Rectangle {
                readonly property real phase: (root.t * 0.55 + index / 4) % 1
                visible: root.showFx
                width: 230; height: 230; radius: 115
                x: 200 - width / 2; y: 240 - height / 2
                color: "transparent"
                border.width: 2
                border.color: Theme.cyan
                scale: 1 + phase * (0.55 + root.micS * 0.9)
                opacity: (root.isListening ? 1 : 0) * (1 - phase) * (0.35 + root.micS * 0.65)
                Behavior on opacity { NumberAnimation { duration: 200 } }
            }
        }

        // holographic numbers orbiting
        Repeater {
            model: root.compact ? 0 : 16
            Text {
                readonly property real ang: index / 16 * Math.PI * 2 + root.t * 0.45
                readonly property real depth: Math.sin(ang) * 0.5 + 0.5
                text: ((index * 7 + Math.floor(root.t * 3)) % 16).toString(16).toUpperCase() + ((index * 3 + Math.floor(root.t * 5)) % 10)
                font.family: Theme.mono
                font.pixelSize: 13
                font.bold: true
                color: root.accent
                x: 200 + Math.cos(ang) * 205 - width / 2
                y: 235 + Math.sin(ang) * 70 - height / 2
                scale: 0.7 + depth * 0.5
                z: depth > 0.5 ? 10 : -1
                opacity: (root.isThinking ? 1 : root.isWorking ? 0.35 : 0) * (0.25 + depth * 0.75)
                Behavior on opacity { NumberAnimation { duration: 300 } }
            }
        }

        // ------------------------------------------------------------ the duck
        Item {
            id: body
            width: 400; height: 500
            y: root.floatY
            x: root.glitch

            Hoodie { part: "body"; accent: root.accent; breathe: root.breathe; glow: root.glowTarget }

            Item {
                id: headGroup
                width: 400; height: 500
                transform: [
                    Rotation { origin.x: 200; origin.y: 350; angle: root.headTilt },
                    Translate { y: root.headNod }
                ]
                scale: 1 + (root.isListening ? 0.025 + root.micS * 0.03 : 0)
                transformOrigin: Item.Bottom

                Hoodie { part: "back"; accent: root.accent; glow: root.glowTarget }
                DuckHead { accent: root.accent; rimLight: root.glowTarget; flush: root.isError ? 1 : 0 }
                Hoodie { part: "shadow" }
                DuckEyes {
                    lookX: root.lookX; lookY: root.lookY
                    lidLeft: root.lidL; lidRight: root.lidR
                    blink: root.blink
                    tiltLeft: root.eyeTilt; tiltRight: -root.eyeTilt
                    browLeftAngle: root.browLA; browRightAngle: root.browRA
                    browLeftLift: root.browLL; browRightLift: root.browRL
                    glow: root.glowTarget
                    irisColor: root.isError ? Theme.red : Theme.cyan
                    pupilScale: root.isListening ? 1.25 : root.isWorking ? 0.8 : 1.0
                }
                DuckBeak { open: root.mouthOpen; smirk: root.smirkTarget }
                Hoodie { part: "rim"; accent: root.accent; glow: root.glowTarget }

                // speaking sound arcs from the beak
                Shape {
                    anchors.fill: parent
                    visible: root.showFx
                    opacity: root.isSpeaking ? 0.25 + root.mouthOpen * 0.75 : 0
                    Behavior on opacity { NumberAnimation { duration: 150 } }
                    preferredRendererType: Shape.CurveRenderer
                    ShapePath {
                        strokeColor: Theme.cyan; strokeWidth: 2.5; fillColor: "transparent"; capStyle: ShapePath.RoundCap
                        PathAngleArc { centerX: 200; centerY: 290; radiusX: 128; radiusY: 128; startAngle: -18; sweepAngle: 36 }
                    }
                    ShapePath {
                        strokeColor: Theme.alpha(Theme.cyan, 0.5); strokeWidth: 2; fillColor: "transparent"; capStyle: ShapePath.RoundCap
                        PathAngleArc { centerX: 200; centerY: 290; radiusX: 146; radiusY: 146; startAngle: -14; sweepAngle: 28 }
                    }
                    ShapePath {
                        strokeColor: Theme.cyan; strokeWidth: 2.5; fillColor: "transparent"; capStyle: ShapePath.RoundCap
                        PathAngleArc { centerX: 200; centerY: 290; radiusX: 128; radiusY: 128; startAngle: 162; sweepAngle: 36 }
                    }
                    ShapePath {
                        strokeColor: Theme.alpha(Theme.cyan, 0.5); strokeWidth: 2; fillColor: "transparent"; capStyle: ShapePath.RoundCap
                        PathAngleArc { centerX: 200; centerY: 290; radiusX: 146; radiusY: 146; startAngle: 166; sweepAngle: 28 }
                    }
                }

                // error: confused question mark
                Text {
                    text: "?"
                    x: 300; y: 60 + Math.sin(root.t * 3) * 6
                    rotation: 14
                    font.family: Theme.font; font.pixelSize: 64; font.bold: true
                    color: Theme.red
                    opacity: root.isError ? 0.95 : 0
                    Behavior on opacity { NumberAnimation { duration: 250 } }
                }
            }

            Hoodie { part: "strings"; accent: root.accent; sway: root.sway; glow: root.glowTarget }
        }

        // listening: reactive side bars ("ears")
        Repeater {
            model: root.compact ? 0 : 14
            Rectangle {
                readonly property bool onLeft: index < 7
                readonly property int i: index % 7
                readonly property real lvl: root.micS * (0.45 + 0.55 * Math.abs(Math.sin(root.t * 9 + i * 1.3)))
                width: 4; radius: 2
                height: 8 + lvl * (60 - Math.abs(i - 3) * 9)
                x: onLeft ? 46 - i * 9 : 350 + i * 9
                y: 240 - height / 2 + root.floatY
                color: Theme.cyan
                opacity: root.isListening ? 0.85 - i * 0.08 : 0
                Behavior on opacity { NumberAnimation { duration: 250 } }
            }
        }

        // working: holographic HUD panels + scanline
        Item {
            id: hud
            visible: opacity > 0.01 && root.showFx && !root.compact
            opacity: root.isWorking ? 1 : 0
            Behavior on opacity { NumberAnimation { duration: 350 } }
            width: 400; height: 500

            Repeater {
                model: 2
                Item {
                    readonly property bool onLeft: index === 0
                    width: 120; height: 96
                    x: onLeft ? -118 : 398
                    y: 150 + Math.sin(root.t * 1.4 + index) * 6
                    transform: Rotation { origin.x: onLeft ? 120 : 0; origin.y: 48; axis { x: 0; y: 1; z: 0 } angle: onLeft ? 18 : -18 }
                    Rectangle {
                        anchors.fill: parent; radius: 6
                        color: Theme.alpha(Theme.cyan, 0.06)
                        border.color: Theme.alpha(Theme.cyan, 0.6); border.width: 1
                    }
                    Text {
                        x: 8; y: 6
                        text: parent.onLeft ? "TASK.EXEC" : "SYS.LINK"
                        font.family: Theme.mono; font.pixelSize: 9; font.bold: true
                        color: Theme.cyan
                    }
                    Column {
                        x: 8; y: 24; spacing: 7
                        Repeater {
                            model: 4
                            Rectangle {
                                width: 104; height: 5; radius: 2
                                color: Theme.alpha(Theme.cyan, 0.15)
                                Rectangle {
                                    height: parent.height; radius: 2
                                    width: parent.width * ((root.t * (0.18 + index * 0.07) + index * 0.31) % 1)
                                    color: index % 2 ? Theme.blue : Theme.cyan
                                }
                            }
                        }
                    }
                    Text {
                        anchors.right: parent.right; anchors.rightMargin: 8; anchors.bottom: parent.bottom; anchors.bottomMargin: 4
                        text: Math.floor((root.t * 23) % 100) + "%"
                        font.family: Theme.mono; font.pixelSize: 10
                        color: Theme.text
                    }
                }
            }
            Rectangle {   // scanline
                readonly property real p: (root.t * 0.45) % 1
                x: 40; width: 320; height: 2
                y: 90 + p * 380
                opacity: Math.sin(Math.PI * p) * 0.8
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: Theme.alpha(Theme.cyan, 0) }
                    GradientStop { position: 0.5; color: Theme.cyan }
                    GradientStop { position: 1; color: Theme.alpha(Theme.cyan, 0) }
                }
            }
        }
    }

    // particles live outside the rig so they span the whole area
    ParticleSystem {
        anchors.fill: parent
        visible: root.showFx && !root.compact
        z: -1
        color: root.accent
        activity: root.isThinking ? 1 : root.isWorking ? 0.8 : root.isListening ? 0.55 : root.isSpeaking ? 0.5 : root.isError ? 0.2 : 0.25
    }
}
