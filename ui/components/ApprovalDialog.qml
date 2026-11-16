import QtQuick
import QtQuick.Layouts

// Modal approval gate for sensitive actions.
Item {
    id: root
    readonly property bool open: backend.approval && backend.approval.id !== undefined
    visible: opacity > 0
    opacity: open ? 1 : 0
    z: 50
    Behavior on opacity { NumberAnimation { duration: 180 } }

    Rectangle { anchors.fill: parent; color: Qt.rgba(0.01, 0.02, 0.04, 0.72) }
    MouseArea { anchors.fill: parent; hoverEnabled: true }

    HolographicPanel {
        anchors.centerIn: parent
        width: Math.min(560, parent.width - 40)
        height: body.implicitHeight + 70
        title: "Onay gerekiyor"
        tag: root.open ? "#" + backend.approval.id : ""
        accent: Theme.amber
        highlighted: true
        ColumnLayout {
            id: body
            anchors.left: parent.left; anchors.right: parent.right
            spacing: 12
            Text { text: root.open ? backend.approval.description : ""; color: Theme.text; font.family: Theme.font; font.pixelSize: 18; font.weight: Font.DemiBold
                   wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Text { text: root.open ? "Görev: " + backend.approval.task : ""; color: Theme.muted; font.family: Theme.font; font.pixelSize: 13; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            RowLayout {
                spacing: 8
                Rectangle {
                    implicitWidth: riskText.implicitWidth + 16; implicitHeight: 22; radius: 11
                    color: Theme.alpha(Theme.amber, 0.15); border.color: Theme.amber
                    Text { id: riskText; anchors.centerIn: parent; text: root.open ? "risk: " + backend.approval.risk : ""; color: Theme.amber; font.family: Theme.mono; font.pixelSize: 11 }
                }
                Text { text: root.open ? backend.approval.action : ""; color: Theme.cyan; font.family: Theme.mono; font.pixelSize: 12 }
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: params.implicitHeight + 16
                radius: 6; color: "#060B12"; border.color: Theme.border
                Text { id: params; anchors.fill: parent; anchors.margins: 8; text: root.open ? backend.approval.params : ""
                       color: Theme.text; font.family: Theme.mono; font.pixelSize: 12; wrapMode: Text.WrapAnywhere }
            }
            Text { text: "VOLB bu işlemi yalnızca sen onaylarsan yapacak. 3 dakika içinde yanıt verilmezse iptal edilir."
                   color: Theme.muted; font.family: Theme.font; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            RowLayout {
                Layout.alignment: Qt.AlignRight
                spacing: 10
                HudButton { text: "Reddet"; danger: true; onClicked: backend.resolveApproval(backend.approval.id, false) }
                HudButton { text: "Onayla"; primary: true; accent: Theme.green; onClicked: backend.resolveApproval(backend.approval.id, true) }
            }
        }
    }
}
