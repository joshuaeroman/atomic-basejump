import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: settingsPage
    title: qsTr("Settings")
    footer: StatusBar {}

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing
        Layout.fillWidth: true
        Layout.maximumWidth: Kirigami.Units.gridUnit * 45
        Layout.alignment: Qt.AlignHCenter

        // Card 0: Appearance
        Kirigami.Card {
            Layout.fillWidth: true
            header: Kirigami.Heading {
                text: qsTr("Appearance")
                level: 3
            }

            contentItem: ColumnLayout {
                spacing: Kirigami.Units.largeSpacing

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.mediumSpacing

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing

                        Controls.Label {
                            text: qsTr("User Interface Theme")
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Controls.Label {
                            text: qsTr("Choose between native KDE or GNOME visual styles, or let the app automatically match your desktop environment.")
                            opacity: 0.7
                            font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                    }

                    Controls.ComboBox {
                        model: [qsTr("Auto"), qsTr("KDE"), qsTr("GNOME")]
                        currentIndex: {
                            var theme = settingsManager.uiTheme;
                            if (theme === "KDE") return 1;
                            if (theme === "GNOME") return 2;
                            return 0;
                        }
                        onActivated: (index) => {
                            if (index === 0) settingsManager.uiTheme = "Auto";
                            else if (index === 1) settingsManager.uiTheme = "KDE";
                            else if (index === 2) settingsManager.uiTheme = "GNOME";
                            restartMessage.visible = true;
                        }
                    }
                }

                Kirigami.InlineMessage {
                    id: restartMessage
                    Layout.fillWidth: true
                    type: Kirigami.MessageType.Information
                    text: qsTr("A restart of the application is required to apply the theme change.")
                    visible: false
                    showCloseButton: true
                }
            }
        }

        // Card 1: Desktop Notifications (tray / app scheduler not shipped)
        Kirigami.Card {
            Layout.fillWidth: true
            header: Kirigami.Heading {
                text: qsTr("Desktop Notifications")
                level: 3
            }

            contentItem: ColumnLayout {
                spacing: Kirigami.Units.largeSpacing

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.mediumSpacing

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing

                        Controls.Label {
                            text: qsTr("Enable Desktop Notifications")
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Controls.Label {
                            text: qsTr("Show desktop notifications for system update events and completed operations")
                            opacity: 0.7
                            font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                    }

                    Controls.Switch {
                        objectName: "notificationsSwitch"
                        checked: settingsManager.enableNotifications
                        onToggled: {
                            // toggled fires for binding-driven changes too; only
                            // act on real user interaction to avoid write-backs.
                            if (checked !== settingsManager.enableNotifications)
                                settingsManager.enableNotifications = checked
                        }
                    }
                }

                Kirigami.Separator { Layout.fillWidth: true }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.mediumSpacing
                    opacity: settingsManager.enableNotifications ? 1.0 : 0.5

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing

                        Controls.Label {
                            text: qsTr("Notify when Update Staged / Reboot Ready")
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Controls.Label {
                            text: qsTr("Display a desktop notification when an update finishes staging.")
                            opacity: 0.7
                            font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                    }

                    Controls.Switch {
                        objectName: "stagedUpdateSwitch"
                        checked: settingsManager.notifyOnStagedUpdate
                        enabled: settingsManager.enableNotifications
                        onToggled: {
                            if (checked !== settingsManager.notifyOnStagedUpdate)
                                settingsManager.notifyOnStagedUpdate = checked
                        }
                    }
                }
            }
        }

        // Card 2: Host System Auto-Update Service
        Kirigami.Card {
            Layout.fillWidth: true
            header: Kirigami.Heading {
                text: qsTr("Host System Auto-Update Service")
                level: 3
            }

            contentItem: ColumnLayout {
                spacing: Kirigami.Units.largeSpacing

                Controls.Label {
                    text: qsTr("Manage the host system background service (rpm-ostreed-automatic.timer) that automatically stages daily system updates.")
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                    opacity: 0.85
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.mediumSpacing

                    Kirigami.Icon {
                        source: settingsManager.systemAutoUpdateEnabled ? "dialog-ok" : "dialog-information"
                        Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
                        Layout.preferredHeight: Kirigami.Units.iconSizes.smallMedium
                    }

                    Controls.Label {
                        text: settingsManager.systemAutoUpdateStatus
                        font.bold: true
                        Layout.fillWidth: true
                    }

                    Controls.Button {
                        text: qsTr("Refresh Status")
                        icon.name: "view-refresh"
                        enabled: !settingsManager.systemAutoUpdateChecking
                        onClicked: settingsManager.refreshSystemAutoUpdateStatus()
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.mediumSpacing
                    opacity: settingsManager.systemAutoUpdateChecking ? 0.5 : 1.0

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing

                        Controls.Label {
                            text: qsTr("Enable Host Daily Auto-Staging Service")
                            font.bold: true
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }

                        Controls.Label {
                            text: qsTr("Enables or disables rpm-ostreed-automatic.timer on the host via pkexec")
                            opacity: 0.7
                            font.pixelSize: Kirigami.Theme.smallFont.pixelSize
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                    }

                    Controls.Switch {
                        objectName: "systemAutoUpdateSwitch"
                        checked: settingsManager.systemAutoUpdateEnabled
                        enabled: !settingsManager.systemAutoUpdateChecking
                        onToggled: {
                            // toggled also fires when the checked binding is
                            // updated by a status refresh; never run pkexec for
                            // a programmatic sync.
                            if (checked !== settingsManager.systemAutoUpdateEnabled)
                                settingsManager.toggleSystemAutoUpdate(checked)
                        }
                    }
                }
            }
        }

        // Card 3: Manual update checks
        Kirigami.Card {
            Layout.fillWidth: true
            header: Kirigami.Heading {
                text: qsTr("Update Checks")
                level: 3
            }

            contentItem: ColumnLayout {
                spacing: Kirigami.Units.largeSpacing

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.largeSpacing

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing

                        Controls.Label {
                            text: qsTr("Last Checked")
                            opacity: 0.7
                        }

                        Controls.Label {
                            text: settingsManager.lastCheckTime
                            font.bold: true
                        }
                    }

                    Controls.Button {
                        text: qsTr("Check for Updates Now")
                        icon.name: "view-refresh"
                        enabled: !backend.transactionInProgress
                        onClicked: settingsManager.checkForUpdatesNow()
                    }
                }
            }
        }
    }
}
