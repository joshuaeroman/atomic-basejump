import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.OverlaySheet {
    id: root
    title: qsTr("Transaction Console Output")

    property string logText: backend.transactionLog
    property string errorText: backend.lastError
    property bool isRunning: backend.transactionInProgress
    property bool autoScroll: true

    function scrollToEnd() {
        if (!logTextArea || logTextArea.text.length === 0)
            return
        logTextArea.cursorPosition = logTextArea.text.length
        var flickable = scrollView.contentItem
        if (flickable)
            flickable.contentY = flickable.contentHeight
    }

    header: RowLayout {
        spacing: Kirigami.Units.mediumSpacing

        Kirigami.Heading {
            text: qsTr("Transaction Console Output")
            level: 2
            Layout.fillWidth: true
        }

        // Live Feed Badge (Visible during active transaction)
        Rectangle {
            visible: root.isRunning
            implicitWidth: liveRow.implicitWidth + Kirigami.Units.largeSpacing
            implicitHeight: Kirigami.Units.gridUnit * 1.5
            color: Qt.rgba(0.1, 0.8, 0.3, 0.15)
            border.color: "#2ecc71"
            border.width: 1
            radius: height / 2

            RowLayout {
                id: liveRow
                anchors.centerIn: parent
                spacing: Kirigami.Units.smallSpacing

                Rectangle {
                    width: 8
                    height: 8
                    radius: 4
                    color: "#2ecc71"

                    SequentialAnimation on opacity {
                        running: root.isRunning
                        loops: Animation.Infinite
                        PropertyAnimation { to: 0.3; duration: 600 }
                        PropertyAnimation { to: 1.0; duration: 600 }
                    }
                }

                Controls.Label {
                    text: qsTr("LIVE FEED")
                    font.pixelSize: Kirigami.Units.gridUnit * 0.75
                    font.bold: true
                    color: "#2ecc71"
                }
            }
        }

        // Transaction Status Badge (Visible when completed/failed)
        Rectangle {
            visible: !root.isRunning && root.logText !== ""
            implicitWidth: statusRow.implicitWidth + Kirigami.Units.largeSpacing
            implicitHeight: Kirigami.Units.gridUnit * 1.5
            color: root.errorText !== "" ? Qt.rgba(0.9, 0.2, 0.2, 0.15) : Qt.rgba(0.2, 0.6, 0.9, 0.15)
            border.color: root.errorText !== "" ? "#e74c3c" : "#3498db"
            border.width: 1
            radius: height / 2

            RowLayout {
                id: statusRow
                anchors.centerIn: parent
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Icon {
                    source: root.errorText !== "" ? "dialog-error" : "emblem-success"
                    Layout.preferredWidth: Kirigami.Units.iconSizes.small * 0.8
                    Layout.preferredHeight: Kirigami.Units.iconSizes.small * 0.8
                }

                Controls.Label {
                    text: root.errorText !== "" ? qsTr("FAILED") : qsTr("COMPLETED")
                    font.pixelSize: Kirigami.Units.gridUnit * 0.75
                    font.bold: true
                    color: root.errorText !== "" ? "#e74c3c" : "#3498db"
                }
            }
        }
    }

    ColumnLayout {
        spacing: Kirigami.Units.mediumSpacing

        Kirigami.InlineMessage {
            id: errorBanner
            type: Kirigami.MessageType.Error
            visible: root.errorText !== ""
            text: root.errorText
            Layout.fillWidth: true
        }

        Rectangle {
            Layout.preferredWidth: Kirigami.Units.gridUnit * 42
            Layout.preferredHeight: Kirigami.Units.gridUnit * 28
            color: "#181825"
            border.color: Qt.rgba(0.5, 0.5, 0.5, 0.3)
            border.width: 1
            radius: Kirigami.Units.smallSpacing

            Controls.ScrollView {
                id: scrollView
                anchors.fill: parent
                anchors.margins: Kirigami.Units.smallSpacing

                Controls.TextArea {
                    id: logTextArea
                    text: root.logText !== "" ? root.logText : qsTr("No console output recorded.")
                    readOnly: true
                    font.family: "monospace"
                    font.pixelSize: Kirigami.Units.gridUnit * 0.8
                    wrapMode: Controls.TextArea.Wrap
                    color: "#cdd6f4"
                    selectByMouse: true
                    background: null

                    onTextChanged: {
                        if (root.autoScroll && logTextArea.text.length > 0) {
                            root.scrollToEnd()
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.mediumSpacing

            Controls.CheckBox {
                id: autoScrollCheck
                text: qsTr("Auto-scroll")
                checked: root.autoScroll
                onCheckedChanged: root.autoScroll = checked
            }

            Controls.Label {
                text: qsTr("%1 lines").arg(root.logText !== "" ? root.logText.split('\n').length - 1 : 0)
                opacity: 0.7
                font.pixelSize: Kirigami.Units.gridUnit * 0.75
            }

            Item { Layout.fillWidth: true }

            Controls.Button {
                text: qsTr("Copy Log")
                icon.name: "edit-copy"
                enabled: root.logText !== ""
                onClicked: {
                    logTextArea.selectAll()
                    logTextArea.copy()
                    logTextArea.deselect()
                }
            }

            Controls.Button {
                text: qsTr("Clear Log")
                icon.name: "edit-clear"
                enabled: root.logText !== "" && !root.isRunning
                onClicked: backend.clearTransactionLog()
            }

            Controls.Button {
                text: qsTr("Close")
                icon.name: "dialog-close"
                onClicked: root.close()
            }
        }
    }
}
