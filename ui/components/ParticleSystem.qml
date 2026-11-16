import QtQuick
import QtQuick.Particles as P

// Floating digital particles + drifting binary digits around VOLB.
Item {
    id: root
    property real activity: 0.3      // 0..1 — how lively the particles are
    property color color: Theme.cyan
    property bool binary: true
    property real t: 0

    FrameAnimation { running: root.visible; onTriggered: root.t += frameTime }

    P.ParticleSystem { id: sys; running: root.visible }

    P.ImageParticle {
        system: sys
        groups: ["dots"]
        source: "qrc:///particleresources/glowdot.png"
        color: root.color
        colorVariation: 0.12
        alpha: 0.55
        entryEffect: P.ImageParticle.Fade
        Behavior on color { ColorAnimation { duration: 400 } }
    }

    P.Emitter {
        system: sys
        group: "dots"
        anchors.centerIn: parent
        width: parent.width * 0.95
        height: parent.height * 0.9
        shape: P.EllipseShape { fill: true }
        emitRate: 6 + 34 * root.activity
        lifeSpan: 3200
        lifeSpanVariation: 1200
        size: 7
        sizeVariation: 5
        endSize: 2
        velocity: P.AngleDirection { angle: 270; angleVariation: 40; magnitude: 14 + 40 * root.activity; magnitudeVariation: 10 }
    }

    P.Turbulence {
        system: sys
        anchors.fill: parent
        strength: 18 + 40 * root.activity
    }

    // binary digits drifting upward
    Repeater {
        model: root.binary ? 22 : 0
        Text {
            id: digit
            readonly property real seed: (index * 9301 + 49297) % 233280 / 233280
            readonly property real speed: 0.06 + seed * 0.08 + root.activity * 0.05
            readonly property real phase: (root.t * speed + seed * 7.3) % 1
            text: Math.floor((root.t * (0.4 + seed) + index) % 2) === 0 ? "0" : "1"
            font.family: Theme.mono
            font.pixelSize: 10 + Math.round(seed * 8)
            color: root.color
            x: root.width * (0.06 + ((seed * 13.7) % 1) * 0.88) + Math.sin(root.t * 0.8 + index) * 6
            y: root.height * (1 - phase)
            opacity: (0.12 + 0.35 * root.activity) * Math.sin(Math.PI * phase)
        }
    }
}
