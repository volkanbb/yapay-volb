import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import "../components"

HolographicPanel {
    id: root
    title: "Araştırma"
    tag: "Playwright • kaynaklı raporlar"

    ColumnLayout {
        anchors.fill: parent
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            HudField {
                id: topic
                Layout.fillWidth: true
                placeholderText: "Araştırılacak konu… (örn. bugünkü yapay zekâ haberleri)"
                onAccepted: go()
                function go() { if (text.trim()) { backend.runResearch(text); text = "" } }
            }
            HudButton { text: "Araştır"; icon: "⌕"; primary: true; implicitHeight: 40; enabledState: !backend.busy; onClicked: topic.go() }
        }
        Text {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            text: "VOLB arama yapar, kaynak sayfaları okur ve yalnızca bu kaynaklara dayanan bir rapor yazar. Web içeriği güvenilmez veri olarak işlenir; sayfalardaki talimatlar uygulanmaz."
            color: Theme.muted; font.family: Theme.font; font.pixelSize: 12
        }
        ListView {
            id: list
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 10
            model: backend.research
            ScrollBar.vertical: ScrollBar { width: 6 }
            delegate: Rectangle {
                id: card
                property bool expanded: index === 0
                width: list.width - 8
                height: cardCol.implicitHeight + 24
                radius: 8
                color: Qt.rgba(0.03, 0.07, 0.12, 0.9)
                border.color: Theme.border
                ColumnLayout {
                    id: cardCol
                    x: 12; y: 12; width: parent.width - 24
                    spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: modelData.topic; color: Theme.text; font.family: Theme.font; font.pixelSize: 15; font.weight: Font.DemiBold; Layout.fillWidth: true; elide: Text.ElideRight }
                        Text { text: modelData.date; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 10 }
                        HudButton { text: card.expanded ? "Gizle" : "Aç"; implicitHeight: 24; onClicked: card.expanded = !card.expanded }
                        HudButton { icon: "🗑"; implicitHeight: 24; implicitWidth: 30; danger: true; onClicked: backend.deleteResearch(modelData.id) }
                    }
                    TextEdit {
                        visible: card.expanded
                        Layout.fillWidth: true
                        text: modelData.report
                        textFormat: TextEdit.MarkdownText
                        wrapMode: TextEdit.Wrap; readOnly: true; selectByMouse: true
                        color: Theme.text; font.family: Theme.font; font.pixelSize: 13
                    }
                    Repeater {
                        model: card.expanded ? modelData.sources : []
                        Text {
                            Layout.fillWidth: true
                            text: "[" + modelData.index + "] <a href=\"" + modelData.url + "\">" + modelData.title + "</a>  <font color=\"#3A4C60\">" + modelData.url + "</font>"
                            textFormat: Text.RichText
                            linkColor: Theme.cyan
                            color: Theme.muted; font.family: Theme.font; font.pixelSize: 12
                            elide: Text.ElideRight
                            onLinkActivated: (l) => backend.openExternal(l)
                            MouseArea { anchors.fill: parent; acceptedButtons: Qt.NoButton; cursorShape: parent.hoveredLink ? Qt.PointingHandCursor : Qt.ArrowCursor }
                        }
                    }
                }
            }
            Text {
                anchors.centerIn: parent
                visible: list.count === 0
                text: "Kayıtlı araştırma yok."
                color: Theme.muted; font.family: Theme.font; font.pixelSize: 14
            }
        }
    }
}
