import QtQuick
import QtQuick.Controls.Basic

// Dark themed ComboBox. Use `values` for the stored values and `labels` for display text.
ComboBox {
    id: root
    property var values: []
    property var labels: []
    property var current
    signal picked(var value)
    model: labels.length ? labels : values
    currentIndex: Math.max(0, values.indexOf(current))
    onActivated: (i) => root.picked(values[i])
    implicitWidth: 220; implicitHeight: 36
    font.family: Theme.font; font.pixelSize: 13

    background: Rectangle {
        radius: 8
        color: Qt.rgba(0.02, 0.04, 0.07, 0.9)
        border.width: 1
        border.color: root.hovered || root.popup.visible ? Theme.alpha(Theme.cyan, 0.8) : Theme.alpha(Theme.cyan, 0.25)
    }
    contentItem: Text {
        leftPadding: 12; rightPadding: 30
        text: root.displayText
        color: Theme.text
        font: root.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    indicator: Text {
        x: root.width - width - 12; anchors.verticalCenter: parent.verticalCenter
        text: "▾"; color: Theme.cyan; font.pixelSize: 14
    }
    delegate: ItemDelegate {
        id: d
        required property int index
        required property var modelData
        width: root.width
        height: 34
        highlighted: root.highlightedIndex === index
        contentItem: Text {
            text: d.modelData
            color: d.highlighted ? Theme.text : Theme.muted
            font: root.font
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }
        background: Rectangle { color: d.highlighted ? Theme.alpha(Theme.cyan, 0.16) : "transparent"; radius: 6 }
    }
    popup: Popup {
        y: root.height + 4
        width: root.width
        implicitHeight: Math.min(contentItem.implicitHeight + 10, 320)
        padding: 5
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
        }
        background: Rectangle { radius: 8; color: "#0B1420"; border.color: Theme.alpha(Theme.cyan, 0.5) }
    }
}
