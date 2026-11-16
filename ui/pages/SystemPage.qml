import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import "../components"

Flickable {
    id: root
    contentHeight: col.implicitHeight
    clip: true
    ScrollBar.vertical: ScrollBar { width: 6 }

    ColumnLayout {
        id: col
        width: root.width
        spacing: 12

        HolographicPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 220
            title: "Sistem Monitörü"
            tag: "çalışma süresi " + backend.uptimeText
            RowLayout {
                anchors.fill: parent
                spacing: 20
                Repeater {
                    model: [
                        { label: "CPU", value: backend.cpu, detail: backend.cpuText },
                        { label: "RAM", value: backend.ram, detail: backend.ramText },
                        { label: "DİSK", value: backend.disk, detail: backend.diskText }
                    ]
                    ColumnLayout {
                        Layout.fillWidth: true
                        RingGauge { Layout.alignment: Qt.AlignHCenter; implicitWidth: 130; implicitHeight: 130; thickness: 9; value: modelData.value; label: modelData.label }
                        Text { Layout.alignment: Qt.AlignHCenter; text: modelData.detail; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 12 }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            HolographicPanel {
                Layout.fillWidth: true; Layout.preferredHeight: 200
                title: "CPU geçmişi"; tag: "90 sn"
                Sparkline { anchors.fill: parent; values: backend.cpuHistory; color: Theme.cyan }
            }
            HolographicPanel {
                Layout.fillWidth: true; Layout.preferredHeight: 200
                title: "RAM geçmişi"; tag: "90 sn"
                Sparkline { anchors.fill: parent; values: backend.ramHistory; color: Theme.blue }
            }
        }

        HolographicPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 84
            title: "GPU"
            Text { text: backend.gpuText || "—"; color: Theme.text; font.family: Theme.mono; font.pixelSize: 14 }
        }

        HolographicPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 70 + backend.topProcesses.length * 28
            title: "En çok bellek kullanan süreçler"
            Column {
                anchors.left: parent.left; anchors.right: parent.right
                spacing: 4
                Repeater {
                    model: backend.topProcesses
                    RowLayout {
                        width: parent.width; height: 24
                        Text { text: modelData.pid; color: Theme.dim; font.family: Theme.mono; font.pixelSize: 11; Layout.preferredWidth: 70 }
                        Text { text: modelData.name; color: Theme.text; font.family: Theme.font; font.pixelSize: 13; Layout.fillWidth: true; elide: Text.ElideRight }
                        Rectangle {
                            Layout.preferredWidth: 160; height: 5; radius: 2.5; color: Theme.alpha(Theme.cyan, 0.1)
                            Rectangle { width: parent.width * Math.min(1, modelData.mem / 25); height: parent.height; radius: 2.5; color: Theme.cyan }
                        }
                        Text { text: modelData.mem.toFixed(1) + "%"; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 11; Layout.preferredWidth: 56; horizontalAlignment: Text.AlignRight }
                    }
                }
            }
        }
    }
}
