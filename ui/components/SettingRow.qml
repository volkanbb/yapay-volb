import QtQuick
import QtQuick.Layouts

// Label + description on the left, control on the right.
RowLayout {
    id: root
    property string label: ""
    property string description: ""
    default property alias control: holder.data
    spacing: 16
    Layout.fillWidth: true
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 2
        Text { text: root.label; color: Theme.text; font.family: Theme.font; font.pixelSize: 14; Layout.fillWidth: true; wrapMode: Text.WordWrap }
        Text {
            visible: root.description.length > 0
            text: root.description; color: Theme.muted; font.family: Theme.font; font.pixelSize: 12
            Layout.fillWidth: true; wrapMode: Text.WordWrap
        }
    }
    Item {
        id: holder
        Layout.preferredWidth: childrenRect.width
        Layout.preferredHeight: childrenRect.height
    }
}
