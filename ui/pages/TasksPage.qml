import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import "../components"

ColumnLayout {
    id: page
    spacing: 12

    SchedulesPanel {
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(300, 70 + Math.max(1, backend.schedules.length) * 60)
    }

HolographicPanel {
    id: root
    Layout.fillWidth: true
    Layout.fillHeight: true
    title: "Görevler"
    tag: backend.tasks.length + " kayıt"

    ListView {
        id: list
        anchors.fill: parent
        clip: true
        spacing: 10
        model: backend.tasks
        ScrollBar.vertical: ScrollBar { width: 6 }
        delegate: Rectangle {
            readonly property bool live: ["completed", "failed", "cancelled"].indexOf(modelData.state) < 0
            width: list.width - 8
            height: tcol.implicitHeight + 24
            radius: 8
            color: Qt.rgba(0.03, 0.07, 0.12, 0.9)
            border.color: live ? Theme.alpha(Theme.taskColor(modelData.state), 0.6) : Theme.border
            ColumnLayout {
                id: tcol
                x: 12; y: 12; width: parent.width - 24
                spacing: 8
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Rectangle {
                        implicitWidth: chip.implicitWidth + 16; implicitHeight: 22; radius: 11
                        color: Theme.alpha(Theme.taskColor(modelData.state), 0.15)
                        border.color: Theme.taskColor(modelData.state)
                        Text { id: chip; anchors.centerIn: parent; text: modelData.stateLabel || modelData.state; color: Theme.taskColor(modelData.state); font.family: Theme.mono; font.pixelSize: 11 }
                    }
                    Text { text: modelData.title; color: Theme.text; font.family: Theme.font; font.pixelSize: 14; font.weight: Font.DemiBold; Layout.fillWidth: true; elide: Text.ElideRight }
                    Text { text: new Date(modelData.created_at * 1000).toLocaleTimeString(Qt.locale("tr_TR"), "HH:mm:ss"); color: Theme.dim; font.family: Theme.mono; font.pixelSize: 10 }
                    HudButton { visible: parent.parent.parent.live; text: "İptal"; danger: true; implicitHeight: 24; onClicked: backend.cancelTask(modelData.id) }
                }
                Rectangle {
                    Layout.fillWidth: true; height: 4; radius: 2
                    color: Theme.alpha(Theme.cyan, 0.1)
                    Rectangle { width: parent.width * (modelData.progress || 0); height: parent.height; radius: 2; color: Theme.taskColor(modelData.state)
                                Behavior on width { NumberAnimation { duration: 300 } } }
                }
                Repeater {
                    model: modelData.steps || []
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8
                        Rectangle { width: 7; height: 7; radius: 3.5; color: Theme.taskColor(modelData.state); Layout.alignment: Qt.AlignTop; Layout.topMargin: 5 }
                        Column {
                            Layout.fillWidth: true
                            Text { text: (index + 1) + ". " + modelData.description + "   ·  " + modelData.action; color: Theme.text; font.family: Theme.font; font.pixelSize: 12; width: parent.width; elide: Text.ElideRight }
                            Text { visible: modelData.result.length > 0; text: modelData.result; color: Theme.muted; font.family: Theme.font; font.pixelSize: 11
                                   width: parent.width; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight }
                        }
                    }
                }
            }
        }
        Text {
            anchors.centerIn: parent
            visible: list.count === 0
            text: "Henüz görev yok. VOLB'a bir iş ver: “Volb, masaüstünde Projeler adında klasör oluştur”"
            color: Theme.muted; font.family: Theme.font; font.pixelSize: 14
        }
    }
}
}
