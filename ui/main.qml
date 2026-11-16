import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import QtQuick.Controls.Basic
import "components"
import "pages"

ApplicationWindow {
    id: win
    width: 1600; height: 960
    minimumWidth: 1000; minimumHeight: 660
    visible: true
    visibility: startWindowed ? Window.Windowed : Window.Maximized
    title: "YAPAY VOLB"
    color: Theme.bg

    property int page: startPage
    readonly property bool compactNav: width < 1300
    readonly property bool showRight: width >= 1180

    readonly property var navItems: [
        { icon: "◈", label: "Dashboard" },
        { icon: "◍", label: "AI Sohbet" },
        { icon: "⌕", label: "Araştırma" },
        { icon: "◎", label: "Tarayıcı" },
        { icon: "☰", label: "Görevler" },
        { icon: "◆", label: "Hafıza" },
        { icon: "▤", label: "Sistem" },
        { icon: "◔", label: "Kullanım" },
        { icon: "⚙", label: "Ayarlar" }
    ]

    // ------------------------------------------------------------------ background
    Item {
        anchors.fill: parent
        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                GradientStop { position: 0; color: "#060B13" }
                GradientStop { position: 1; color: "#03060B" }
            }
        }
        Canvas {
            id: grid
            anchors.fill: parent
            opacity: 0.55
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                const ctx = getContext("2d")
                ctx.reset()
                ctx.strokeStyle = "rgba(0, 217, 255, 0.045)"
                ctx.lineWidth = 1
                const s = 42
                for (let x = 0; x < width; x += s) { ctx.beginPath(); ctx.moveTo(x + 0.5, 0); ctx.lineTo(x + 0.5, height); ctx.stroke() }
                for (let y = 0; y < height; y += s) { ctx.beginPath(); ctx.moveTo(0, y + 0.5); ctx.lineTo(width, y + 0.5); ctx.stroke() }
                ctx.fillStyle = "rgba(0, 217, 255, 0.16)"
                for (let x2 = 0; x2 < width; x2 += s * 4) for (let y2 = 0; y2 < height; y2 += s * 4) ctx.fillRect(x2 - 1, y2 - 1, 3, 3)
            }
        }
        Rectangle {   // central glow
            width: parent.width * 0.9; height: width
            anchors.centerIn: parent
            radius: width / 2
            opacity: 0.5
            gradient: Gradient {
                GradientStop { position: 0.0; color: "transparent" }
                GradientStop { position: 0.5; color: Qt.rgba(0.09, 0.42, 1, 0.05) }
                GradientStop { position: 1.0; color: "transparent" }
            }
        }
    }

    // ------------------------------------------------------------------ layout
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 10

        // top bar
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 44
            Row {
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12
                Rectangle {
                    width: 34; height: 34; radius: 9
                    color: Theme.alpha(Theme.cyan, 0.12)
                    border.color: Theme.alpha(Theme.cyan, 0.6)
                    VolbCharacter { anchors.fill: parent; anchors.margins: -6; compact: true; showFx: false; mood: backend.state }
                    clip: true
                }
                Column {
                    anchors.verticalCenter: parent.verticalCenter
                    Text { text: "YAPAY VOLB"; color: Theme.text; font.family: Theme.font; font.pixelSize: 19; font.weight: Font.Bold; font.letterSpacing: 5 }
                    Text { text: "PERSONAL AI CORE  //  v" + backend.appVersion; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 9; font.letterSpacing: 2 }
                }
            }
            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                spacing: 18
                Rectangle {
                    visible: backend.sleepInhibited
                    anchors.verticalCenter: parent.verticalCenter
                    implicitWidth: sleepTxt.implicitWidth + 18; implicitHeight: 22; radius: 11
                    color: Theme.alpha(Theme.blue, 0.15); border.color: Theme.alpha(Theme.blue, 0.6)
                    Text { id: sleepTxt; anchors.centerIn: parent; text: "☾ UYKU ENGELLİ"; color: Theme.text
                           font.family: Theme.mono; font.pixelSize: 10; font.letterSpacing: 1.2 }
                    MouseArea { id: sleepMa; anchors.fill: parent; hoverEnabled: true; onClicked: win.page = 8 }
                    ToolTip.visible: sleepMa.containsMouse
                    ToolTip.text: backend.sleepReason + " (Ayarlar → Uyku kipini engelle)"
                }
                Row {
                    spacing: 8
                    anchors.verticalCenter: parent.verticalCenter
                    Rectangle {
                        width: 8; height: 8; radius: 4; anchors.verticalCenter: parent.verticalCenter
                        color: backend.claudeConnected ? Theme.green : Theme.amber
                        SequentialAnimation on opacity { loops: Animation.Infinite; NumberAnimation { to: 0.35; duration: 900 } NumberAnimation { to: 1; duration: 900 } }
                    }
                    Text { text: backend.claudeConnected ? "CLAUDE ONLINE" : "CLAUDE OFFLINE"; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 11; font.letterSpacing: 1.5 }
                }
                Text {
                    id: clock
                    anchors.verticalCenter: parent.verticalCenter
                    color: Theme.text
                    font.family: Theme.mono; font.pixelSize: 15
                    Timer { running: true; repeat: true; interval: 1000; triggeredOnStart: true
                            onTriggered: clock.text = Qt.formatDateTime(new Date(), "dd.MM.yyyy  HH:mm:ss") }
                }
            }
            Rectangle { anchors.bottom: parent.bottom; anchors.bottomMargin: -6; width: parent.width; height: 1
                gradient: Gradient { orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: Theme.alpha(Theme.cyan, 0.5) }
                    GradientStop { position: 0.5; color: Theme.alpha(Theme.cyan, 0.08) }
                    GradientStop { position: 1; color: Theme.alpha(Theme.cyan, 0.4) } } }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12

            // ---------------------------------------------------------- left navigation
            HolographicPanel {
                Layout.fillHeight: true
                Layout.preferredWidth: win.compactNav ? 64 : 206
                padding: 8
                Column {
                    anchors.fill: parent
                    anchors.topMargin: 6
                    spacing: 4
                    Repeater {
                        model: win.navItems
                        Rectangle {
                            width: parent.width; height: 46; radius: 8
                            readonly property bool active: win.page === index
                            color: active ? Theme.alpha(Theme.cyan, 0.14) : navMa.containsMouse ? Theme.alpha(Theme.cyan, 0.06) : "transparent"
                            border.color: active ? Theme.alpha(Theme.cyan, 0.55) : "transparent"
                            Rectangle { visible: parent.active; width: 3; height: 22; radius: 1.5; color: Theme.cyan; anchors.verticalCenter: parent.verticalCenter; x: 1 }
                            Row {
                                anchors.verticalCenter: parent.verticalCenter
                                x: win.compactNav ? (parent.width - 20) / 2 : 16
                                spacing: 14
                                Text { text: modelData.icon; width: 20; horizontalAlignment: Text.AlignHCenter
                                       color: parent.parent.active ? Theme.cyan : Theme.muted; font.pixelSize: 18 }
                                Text { visible: !win.compactNav; text: modelData.label
                                       color: parent.parent.active ? Theme.text : Theme.muted
                                       font.family: Theme.font; font.pixelSize: 14; font.weight: parent.parent.active ? Font.DemiBold : Font.Normal
                                       anchors.verticalCenter: parent.verticalCenter }
                            }
                            MouseArea { id: navMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: win.page = index }
                            ToolTip.visible: win.compactNav && navMa.containsMouse
                            ToolTip.text: modelData.label
                        }
                    }
                }
                Column {
                    visible: !win.compactNav
                    anchors.bottom: parent.bottom
                    width: parent.width
                    spacing: 4
                    Text { text: "DURUM"; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 10; font.letterSpacing: 2; x: 8 }
                    Text { text: Theme.stateLabel(backend.state); color: Theme.stateColor(backend.state); font.family: Theme.mono; font.pixelSize: 13; font.bold: true; x: 8 }
                    Text { text: "F2 sürekli dinleme · Esc durdur"; color: Theme.dim; font.family: Theme.font; font.pixelSize: 10; x: 8; width: parent.width - 16; wrapMode: Text.WordWrap }
                }
            }

            // ---------------------------------------------------------- pages
            StackLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                currentIndex: win.page
                DashboardPage {}
                ChatPage {}
                ResearchPage {}
                BrowserPage {}
                TasksPage {}
                MemoryPage {}
                SystemPage {}
                UsagePage {}
                SettingsPage {}
            }

            // ---------------------------------------------------------- right status panel
            RightPanel {
                visible: win.showRight
                Layout.fillHeight: true
                Layout.preferredWidth: 300
            }
        }

        BottomBar {
            Layout.fillWidth: true
            Layout.preferredHeight: 72
        }
    }

    ApprovalDialog { anchors.fill: parent }

    // ------------------------------------------------------------------ toasts
    ListModel { id: toasts }
    Connections {
        target: backend
        function onToast(message, kind) {
            toasts.append({ msg: message, kind: kind, born: Date.now() })
            toastCleanup.start()
        }
    }
    Timer {
        id: toastCleanup
        interval: 4500; repeat: true
        onTriggered: {
            const now = Date.now()
            for (let i = toasts.count - 1; i >= 0; i--) if (now - toasts.get(i).born > 4200) toasts.remove(i)
            if (toasts.count === 0) stop()
        }
    }
    Column {
        anchors.top: parent.top; anchors.topMargin: 70
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 8
        z: 100
        Repeater {
            model: toasts
            Rectangle {
                readonly property color tone: kind === "error" ? Theme.red : kind === "warn" ? Theme.amber : kind === "ok" ? Theme.green : Theme.cyan
                width: Math.min(560, toastText.implicitWidth + 40); height: toastText.implicitHeight + 20; radius: 8
                color: "#0D1826"; border.color: tone
                Text { id: toastText; anchors.centerIn: parent; width: Math.min(520, implicitWidth); text: msg; color: Theme.text; wrapMode: Text.WordWrap; font.family: Theme.font; font.pixelSize: 13 }
                MouseArea { anchors.fill: parent; onClicked: toasts.remove(index) }
            }
        }
    }

    // ------------------------------------------------------------------ shortcuts
    Shortcut { sequence: "F2"; onActivated: backend.setContinuous(!backend.continuous) }
    Shortcut { sequence: "Esc"; onActivated: backend.stopAll() }
    Repeater {
        model: 9
        Item { Shortcut { sequence: "Ctrl+" + (index + 1); onActivated: win.page = index } }
    }
}
