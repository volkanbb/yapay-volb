import QtQuick

// Chat bubble with markdown, selectable text and clickable links.
Item {
    id: root
    property string role: "assistant"
    property string text: ""
    property string time: ""
    property bool done: true
    property real maxWidth: 600
    readonly property bool mine: role === "user"
    width: parent ? parent.width : 400
    height: bubble.height + 22

    Text {
        x: root.mine ? root.width - width - 4 : 4
        text: (root.mine ? "SEN" : "VOLB") + "  ·  " + root.time
        color: root.mine ? Theme.muted : Theme.cyan
        font.family: Theme.mono; font.pixelSize: 10; font.letterSpacing: 1.5
    }
    Rectangle {
        id: bubble
        y: 18
        x: root.mine ? root.width - width : 0
        width: Math.min(root.maxWidth, Math.max(60, body.implicitWidth + 28))
        height: body.implicitHeight + 22
        radius: 10
        color: root.mine ? Qt.rgba(0.09, 0.42, 1, 0.16) : Qt.rgba(0.04, 0.09, 0.15, 0.92)
        border.color: root.mine ? Theme.alpha(Theme.blue, 0.5) : Theme.alpha(Theme.cyan, 0.28)
        TextEdit {
            id: body
            x: 14; y: 11
            width: Math.min(root.maxWidth - 28, implicitWidth)
            text: root.text.length ? root.text : "…"
            textFormat: TextEdit.MarkdownText
            wrapMode: TextEdit.Wrap
            readOnly: true
            selectByMouse: true
            color: Theme.text
            selectionColor: Theme.alpha(Theme.cyan, 0.4)
            font.family: Theme.font; font.pixelSize: 14
            onLinkActivated: (link) => backend.openExternal(link)
            Component.onCompleted: width = Qt.binding(() => Math.min(root.maxWidth - 28, implicitWidth))
        }
        Rectangle {
            visible: !root.done && !root.mine
            width: 8; height: 8; radius: 4; color: Theme.cyan
            anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 6
            SequentialAnimation on opacity { loops: Animation.Infinite; NumberAnimation { to: 0.2; duration: 400 } NumberAnimation { to: 1; duration: 400 } }
        }
    }
}
