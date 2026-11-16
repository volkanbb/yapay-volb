import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import "../components"

HolographicPanel {
    id: root
    title: "Tarayıcı"
    tag: "Chromium • " + backend.browserStatus

    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            HudField {
                id: url
                Layout.fillWidth: true
                placeholderText: "https://… adresi (VOLB'un kontrol ettiği Chromium'da açılır)"
                onAccepted: go()
                function go() { if (text.trim()) backend.browserOpen(text.trim()) }
            }
            HudButton { text: "Yeni sekmede aç"; icon: "◎"; primary: true; implicitHeight: 40; onClicked: url.go() }
            HudButton { icon: "⟳"; implicitHeight: 40; implicitWidth: 40; onClicked: backend.browserRefresh() }
            HudButton { text: "Kapat"; danger: true; implicitHeight: 40; onClicked: backend.browserStop() }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 12
            ColumnLayout {
                Layout.preferredWidth: Math.max(280, root.width * 0.38)
                Layout.fillHeight: true
                spacing: 8
                SectionTitle { text: "Sekmeler" }
                ListView {
                    id: tabs
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    spacing: 6
                    model: backend.browserTabs
                    delegate: Rectangle {
                        width: tabs.width; height: 58; radius: 8
                        color: Qt.rgba(0.03, 0.07, 0.12, 0.9); border.color: Theme.border
                        Column {
                            x: 12; y: 9; width: parent.width - 130
                            Text { text: modelData.title || "(başlıksız)"; color: Theme.text; font.family: Theme.font; font.pixelSize: 13; elide: Text.ElideRight; width: parent.width }
                            Text { text: modelData.url; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 10; elide: Text.ElideMiddle; width: parent.width }
                        }
                        Row {
                            anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
                            spacing: 6
                            HudButton { icon: "📷"; implicitHeight: 28; implicitWidth: 34; onClicked: backend.browserScreenshot(modelData.index) }
                            HudButton { icon: "✕"; danger: true; implicitHeight: 28; implicitWidth: 34; onClicked: backend.browserCloseTab(modelData.index) }
                        }
                    }
                    Text {
                        anchors.centerIn: parent; width: parent.width - 20
                        visible: tabs.count === 0
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                        text: "Açık sekme yok. Bir adres girip aç; araştırmalar da bu tarayıcıyı kullanır."
                        color: Theme.muted; font.family: Theme.font; font.pixelSize: 13
                    }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 8
                SectionTitle { text: "Son sayfa görüntüsü" }
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 8; color: "#03060A"; border.color: Theme.border
                    clip: true
                    Image {
                        anchors.fill: parent; anchors.margins: 6
                        source: backend.lastScreenshot
                        fillMode: Image.PreserveAspectFit
                        asynchronous: true
                        cache: false
                    }
                    Text {
                        anchors.centerIn: parent
                        visible: backend.lastScreenshot.length === 0
                        text: "Henüz görüntü yok"
                        color: Theme.dim; font.family: Theme.font; font.pixelSize: 13
                    }
                    MouseArea { anchors.fill: parent; enabled: backend.lastScreenshot.length > 0; cursorShape: Qt.PointingHandCursor; onClicked: backend.openPath(backend.lastScreenshot) }
                }
            }
        }
    }
}
