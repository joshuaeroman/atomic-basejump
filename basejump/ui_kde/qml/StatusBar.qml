import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Controls.ToolBar {
    id: root
    visible: backend.transactionInProgress || backend.transactionLog !== "" || (backend.transactionMessage !== "" && backend.transactionMessage !== undefined)
    implicitHeight: Kirigami.Units.gridUnit * 2.5

    background: Rectangle {
        color: Kirigami.Theme.backgroundColor
        Rectangle {
            width: parent.width
            height: 1
            color: Qt.rgba(0.5, 0.5, 0.5, 0.2)
            anchors.top: parent.top
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Kirigami.Units.largeSpacing
        anchors.rightMargin: Kirigami.Units.largeSpacing
        anchors.topMargin: Kirigami.Units.smallSpacing
        anchors.bottomMargin: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.mediumSpacing

        Controls.BusyIndicator {
            running: backend.transactionInProgress
            visible: backend.transactionInProgress
            Layout.preferredHeight: Kirigami.Units.iconSizes.small
            Layout.preferredWidth: Kirigami.Units.iconSizes.small
        }

        Kirigami.Icon {
            visible: !backend.transactionInProgress && backend.transactionLog !== ""
            source: backend.lastError !== "" ? "dialog-error" : "emblem-success"
            Layout.preferredHeight: Kirigami.Units.iconSizes.small
            Layout.preferredWidth: Kirigami.Units.iconSizes.small
        }

        Controls.Label {
            text: backend.currentTask !== "" ? "[" + backend.currentTask + "]" : ""
            visible: backend.currentTask !== ""
            font.bold: true
            color: Kirigami.Theme.highlightColor
        }

        Controls.Label {
            text: backend.transactionMessage !== "" ? backend.transactionMessage : (backend.lastError !== "" ? backend.lastError : (backend.transactionLog !== "" ? qsTr("Transaction output logged.") : ""))
            Layout.fillWidth: true
            elide: Text.ElideRight
            font.weight: backend.transactionInProgress ? Font.Medium : Font.Normal
        }

        Controls.Label {
            text: backend.transactionProgress + "%"
            visible: backend.transactionInProgress && backend.transactionProgress > 0
            font.bold: true
            opacity: 0.8
        }

        Controls.ProgressBar {
            value: backend.transactionProgress / 100.0
            visible: backend.transactionInProgress && backend.transactionProgress > 0
            Layout.preferredWidth: 150
        }

        Controls.Button {
            text: qsTr("View Log")
            icon.name: "utilities-terminal"
            visible: backend.transactionLog !== ""
            highlighted: backend.transactionInProgress
            onClicked: globalLogDialog.open()
        }

        Controls.Button {
            icon.name: "edit-clear"
            display: Controls.AbstractButton.IconOnly
            Controls.ToolTip.text: qsTr("Clear Log & Dismiss")
            Controls.ToolTip.visible: hovered
            visible: !backend.transactionInProgress && backend.transactionLog !== ""
            onClicked: backend.clearTransactionLog()
        }

    }
}
