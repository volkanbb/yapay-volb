import QtQuick

Row {
    property string text: ""
    spacing: 10
    Rectangle { width: 3; height: 16; color: Theme.cyan; anchors.verticalCenter: parent.verticalCenter }
    Text {
        text: parent.text.toUpperCase()
        color: Theme.text
        font.family: Theme.font; font.pixelSize: 13; font.weight: Font.DemiBold; font.letterSpacing: 2.5
    }
}
