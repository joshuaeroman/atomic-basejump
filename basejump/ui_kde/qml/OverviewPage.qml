import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: qsTr("Deployments")
    footer: StatusBar {}

    function formatPackageName(str) {
        if (!str) return ""
        var s = str.toString().trim()
        var idx = s.lastIndexOf("/")
        if (idx !== -1) {
            s = s.substring(idx + 1)
        }
        return s
    }

    actions: [
        Kirigami.Action {
            text: qsTr("Check for Updates")
            icon.name: "view-refresh"
            enabled: !backend.transactionInProgress
            onTriggered: backend.checkForUpdates()
        },
        Kirigami.Action {
            text: qsTr("Upgrade System")
            icon.name: "system-software-update"
            visible: backend.updateAvailable && !backend.rebootRequired
            enabled: !backend.transactionInProgress
            onTriggered: backend.upgradeSystem()
        },
        Kirigami.Action {
            text: qsTr("Reboot")
            icon.name: "system-reboot"
            visible: backend.rebootRequired
            enabled: !backend.transactionInProgress
            onTriggered: backend.rebootSystem()
        },
        Kirigami.Action {
            text: qsTr("Refresh")
            icon.name: "view-refresh"
            onTriggered: backend.refreshStatus()
        }
    ]

    property bool plasmaRepairDismissed: false
    property var targetDepData: ({})

    Connections {
        target: backend
        function onStatusChanged() {
            if (!backend.plasmaLoginRepairAvailable)
                page.plasmaRepairDismissed = false
        }
    }

    ListView {
        id: deploymentsList
        model: backend.deployments
        spacing: Kirigami.Units.mediumSpacing

        header: ColumnLayout {
            width: deploymentsList.width
            spacing: Kirigami.Units.largeSpacing

            // Status Banner InlineMessage
            Kirigami.InlineMessage {
                id: statusBanner
                Layout.fillWidth: true
                visible: text !== ""
                text: backend.statusBannerMessage
                type: backend.statusBannerType === "warning" ? Kirigami.MessageType.Warning :
                      backend.statusBannerType === "error" ? Kirigami.MessageType.Error :
                      backend.statusBannerType === "success" ? Kirigami.MessageType.Positive :
                      Kirigami.MessageType.Information

                actions: [
                    Kirigami.Action {
                        text: qsTr("Update Now")
                        visible: backend.updateAvailable && !backend.rebootRequired
                        enabled: !backend.transactionInProgress
                        onTriggered: backend.upgradeSystem()
                    },
                    Kirigami.Action {
                        text: qsTr("Reboot Now")
                        icon.name: "system-reboot"
                        visible: backend.rebootRequired
                        enabled: !backend.transactionInProgress
                        onTriggered: backend.rebootSystem()
                    }
                ]
            }

            // Recovery: staged Plasma deploy while booted on non-Plasma (GNOME → Plasma lockout risk)
            Kirigami.InlineMessage {
                id: plasmaLoginRepairBanner
                Layout.fillWidth: true
                type: Kirigami.MessageType.Warning
                visible: backend.plasmaLoginRepairAvailable && !page.plasmaRepairDismissed
                text: qsTr("Repair pending Plasma login: a Plasma deployment is staged while you are on a non-Plasma system. Without repairing login accounts, the next Plasma boot may show a black screen.")

                actions: [
                    Kirigami.Action {
                        text: qsTr("Repair now")
                        icon.name: "tools-wizard"
                        enabled: !backend.transactionInProgress
                        onTriggered: backend.prepPlasmaLoginAccounts(true)
                    },
                    Kirigami.Action {
                        text: qsTr("Dismiss")
                        enabled: true
                        onTriggered: page.plasmaRepairDismissed = true
                    }
                ]
            }

            // Active Transaction Progress Card
            Kirigami.Card {
                Layout.fillWidth: true
                visible: backend.transactionInProgress

                header: Kirigami.Heading {
                    text: qsTr("Transaction in Progress...")
                    level: 3
                }

                contentItem: ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing

                    RowLayout {
                        Layout.fillWidth: true

                        Controls.Label {
                            text: backend.transactionMessage
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }

                        Controls.Button {
                            text: qsTr("View Log")
                            icon.name: "utilities-terminal"
                            visible: backend.transactionLog !== ""
                            onClicked: globalLogDialog.open()
                        }
                    }

                    Controls.ProgressBar {
                        Layout.fillWidth: true
                        value: backend.transactionProgress / 100.0
                    }
                }
            }

            Item {
                implicitHeight: Kirigami.Units.smallSpacing
            }
        }

        delegate: Kirigami.Card {
            id: depCard
            width: deploymentsList.width

            header: RowLayout {
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Heading {
                    text: qsTr("Deployment #%1").arg(index)
                    level: 3
                }

                Rectangle {
                    visible: modelData["booted"] === true
                    implicitWidth: bootedLabel.implicitWidth + 12
                    implicitHeight: bootedLabel.implicitHeight + 6
                    radius: 4
                    color: Kirigami.Theme.highlightColor

                    Controls.Label {
                        id: bootedLabel
                        anchors.centerIn: parent
                        text: qsTr("Booted")
                        color: Kirigami.Theme.highlightedTextColor
                        font.pixelSize: Kirigami.Units.gridUnit * 0.75
                        font.bold: true
                    }
                }

                Rectangle {
                    visible: modelData["staged"] === true
                    implicitWidth: stagedLabel.implicitWidth + 12
                    implicitHeight: stagedLabel.implicitHeight + 6
                    radius: 4
                    color: Kirigami.Theme.neutralTextColor

                    Controls.Label {
                        id: stagedLabel
                        anchors.centerIn: parent
                        text: qsTr("Staged / Pending Reboot")
                        color: "#ffffff"
                        font.pixelSize: Kirigami.Units.gridUnit * 0.75
                        font.bold: true
                    }
                }

                Rectangle {
                    visible: modelData["pinned"] === true
                    implicitWidth: pinnedLabel.implicitWidth + 12
                    implicitHeight: pinnedLabel.implicitHeight + 6
                    radius: 4
                    color: Qt.alpha(Kirigami.Theme.positiveTextColor, 0.2)
                    border.color: Kirigami.Theme.positiveTextColor
                    border.width: 1

                    Controls.Label {
                        id: pinnedLabel
                        anchors.centerIn: parent
                        text: qsTr("Pinned")
                        color: Kirigami.Theme.positiveTextColor
                        font.pixelSize: Kirigami.Units.gridUnit * 0.75
                        font.bold: true
                    }
                }

                Item { Layout.fillWidth: true }

                Controls.Button {
                    text: modelData["pinned"] === true ? qsTr("Unpin") : qsTr("Pin")
                    icon.name: modelData["pinned"] === true ? "pin-delete" : "pin"
                    onClicked: {
                        if (modelData["pinned"] === true) {
                            backend.unpinDeployment(index)
                        } else {
                            backend.pinDeployment(index)
                        }
                    }
                }

                Controls.Button {
                    text: qsTr("Rollback")
                    icon.name: "edit-undo"
                    visible: modelData["booted"] !== true && modelData["staged"] !== true && !backend.transactionInProgress
                    onClicked: backend.rollbackSystem()
                }
            }

            contentItem: Kirigami.FormLayout {
                Controls.Label {
                    Kirigami.FormData.label: qsTr("OS / Version:")
                    text: (modelData["osname"] || backend.currentOsName) + " (" + (modelData["version"] || "N/A") + ")"
                    font.bold: true
                }

                Controls.Label {
                    Kirigami.FormData.label: qsTr("Container Image:")
                    text: modelData["container-image-reference"] || qsTr("N/A (Standard Ostree)")
                    wrapMode: Text.WrapAnywhere
                    Layout.fillWidth: true
                }

                Controls.Label {
                    Kirigami.FormData.label: qsTr("Commit Checksum:")
                    text: (modelData["checksum"] || "").substring(0, 20)
                    font.family: "Monospace"
                }

                // Package Overlays Section (2-Column Layout)
                RowLayout {
                    Kirigami.FormData.label: qsTr("Package Overlays:")
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.largeSpacing

                    // Left Column: Package Listings (3 Rows)
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        spacing: Kirigami.Units.mediumSpacing

                        // Row 1: Layered Packages
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Controls.Label {
                                text: qsTr("Layered Packages:")
                                font.bold: true
                            }

                            Flow {
                                Layout.fillWidth: true
                                width: parent ? parent.width : 0
                                spacing: Kirigami.Units.smallSpacing

                                Repeater {
                                    model: modelData["requested-packages"] || []
                                    delegate: Rectangle {
                                        implicitWidth: depPkgLabel.implicitWidth + 12
                                        implicitHeight: depPkgLabel.implicitHeight + 6
                                        radius: 4
                                        color: Qt.alpha(Kirigami.Theme.highlightColor, 0.2)
                                        border.color: Kirigami.Theme.highlightColor
                                        border.width: 1

                                        Controls.Label {
                                            id: depPkgLabel
                                            anchors.centerIn: parent
                                            text: modelData
                                            font.pixelSize: Kirigami.Units.gridUnit * 0.75
                                        }
                                    }
                                }

                                Controls.Label {
                                    visible: !(modelData["requested-packages"]) || modelData["requested-packages"].length === 0
                                    text: qsTr("None")
                                    font.italic: true
                                    color: Kirigami.Theme.disabledTextColor
                                }
                            }
                        }

                        // Row 2: Local Packages
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Controls.Label {
                                text: qsTr("Local Packages:")
                                font.bold: true
                            }

                            Flow {
                                Layout.fillWidth: true
                                width: parent ? parent.width : 0
                                spacing: Kirigami.Units.smallSpacing

                                Repeater {
                                    model: modelData["requested-local-packages"] || []
                                    delegate: Rectangle {
                                        implicitWidth: depLocalPkgLabel.implicitWidth + 12
                                        implicitHeight: depLocalPkgLabel.implicitHeight + 6
                                        radius: 4
                                        color: Qt.alpha(Kirigami.Theme.positiveTextColor, 0.15)
                                        border.color: Kirigami.Theme.positiveTextColor
                                        border.width: 1

                                        Controls.Label {
                                            id: depLocalPkgLabel
                                            anchors.centerIn: parent
                                            text: formatPackageName(modelData)
                                            font.pixelSize: Kirigami.Units.gridUnit * 0.75
                                        }

                                        Controls.ToolTip.visible: (modelData || "").indexOf("/") !== -1 && depLocMouse.containsMouse
                                        Controls.ToolTip.text: modelData

                                        MouseArea {
                                            id: depLocMouse
                                            anchors.fill: parent
                                            hoverEnabled: true
                                        }
                                    }
                                }

                                Controls.Label {
                                    visible: !(modelData["requested-local-packages"]) || modelData["requested-local-packages"].length === 0
                                    text: qsTr("None")
                                    font.italic: true
                                    color: Kirigami.Theme.disabledTextColor
                                }
                            }
                        }

                        // Row 3: Removed Packages
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Controls.Label {
                                text: qsTr("Removed Packages:")
                                font.bold: true
                            }

                            Flow {
                                Layout.fillWidth: true
                                width: parent ? parent.width : 0
                                spacing: Kirigami.Units.smallSpacing

                                Repeater {
                                    model: modelData["requested-base-removals"] || []
                                    delegate: Rectangle {
                                        implicitWidth: depRemPkgLabel.implicitWidth + 12
                                        implicitHeight: depRemPkgLabel.implicitHeight + 6
                                        radius: 4
                                        color: Qt.alpha(Kirigami.Theme.negativeTextColor, 0.15)
                                        border.color: Kirigami.Theme.negativeTextColor
                                        border.width: 1

                                        Controls.Label {
                                            id: depRemPkgLabel
                                            anchors.centerIn: parent
                                            text: modelData
                                            font.pixelSize: Kirigami.Units.gridUnit * 0.75
                                        }
                                    }
                                }

                                Controls.Label {
                                    visible: !(modelData["requested-base-removals"]) || modelData["requested-base-removals"].length === 0
                                    text: qsTr("None")
                                    font.italic: true
                                    color: Kirigami.Theme.disabledTextColor
                                }
                            }
                        }
                    }

                    // Right Column: Action Buttons (Spans all 3 rows)
                    ColumnLayout {
                        Layout.alignment: Qt.AlignTop | Qt.AlignRight
                        Layout.fillWidth: false
                        Layout.preferredWidth: implicitWidth
                        spacing: Kirigami.Units.smallSpacing

                        Controls.Button {
                            icon.name: "document-save"
                            text: qsTr("Save as Overlay Set")
                            Layout.fillWidth: true
                            onClicked: {
                                targetDepData = modelData
                                saveSetDialog.open()
                            }
                        }

                        Controls.Button {
                            icon.name: "layers"
                            text: qsTr("Override Overlays")
                            Layout.fillWidth: true
                            onClicked: {
                                overrideOverlayDialog.open()
                            }
                        }
                    }
                }
            }
        }
    }

    // Save Overlay Set Dialog
    Kirigami.Dialog {
        id: saveSetDialog
        title: qsTr("Save Deployment Package State as Overlay Set")
        padding: Kirigami.Units.largeSpacing

        customFooterActions: [
            Kirigami.Action {
                text: qsTr("Save Overlay Set")
                icon.name: "document-save"
                onTriggered: {
                    var layered = targetDepData["requested-packages"] || []
                    var local = targetDepData["requested-local-packages"] || []
                    var removed = targetDepData["requested-base-removals"] || []
                    overlayService.createOverlaySet(
                        setNameInput.text,
                        setDescInput.text,
                        layered,
                        local,
                        removed
                    )
                    saveSetDialog.close()
                }
            },
            Kirigami.Action {
                text: qsTr("Cancel")
                icon.name: "dialog-cancel"
                onTriggered: saveSetDialog.close()
            }
        ]

        ColumnLayout {
            spacing: Kirigami.Units.mediumSpacing

            Kirigami.FormLayout {
                Layout.fillWidth: true

                Controls.TextField {
                    id: setNameInput
                    Kirigami.FormData.label: qsTr("Profile Name:")
                    placeholderText: "Deployment Overlay Profile"
                    text: (targetDepData["osname"] || "Deployment") + " Overlay Set"
                    Layout.fillWidth: true
                }

                Controls.TextField {
                    id: setDescInput
                    Kirigami.FormData.label: qsTr("Description:")
                    placeholderText: "Saved from deployment"
                    Layout.fillWidth: true
                }
            }
        }
    }

    // Override Overlays Dialog
    Kirigami.Dialog {
        id: overrideOverlayDialog
        title: qsTr("Override System Overlay Set")
        padding: Kirigami.Units.largeSpacing

        readonly property var overlayChoices: {
            var list = []
            var saved = overlayService.overlaySets || []
            for (var i = 0; i < saved.length; ++i) {
                list.push(saved[i])
            }
            // Always available: clear every package overlay and start fresh
            list.push({ name: qsTr("Remove all overlays (start fresh)"), id: "__reset_all__" })
            return list
        }
        property var selectedSet: (overrideCombo.currentIndex >= 0 && overrideOverlayDialog.overlayChoices.length > overrideCombo.currentIndex)
                                  ? overrideOverlayDialog.overlayChoices[overrideCombo.currentIndex]
                                  : null
        readonly property bool isResetSelection: selectedSet && selectedSet.id === "__reset_all__"

        customFooterActions: [
            Kirigami.Action {
                text: overrideOverlayDialog.isResetSelection ? qsTr("Remove All Overlays") : qsTr("Apply to System")
                icon.name: overrideOverlayDialog.isResetSelection ? "edit-clear-all" : "dialog-ok-apply"
                enabled: overrideOverlayDialog.selectedSet !== null
                onTriggered: {
                    var selected = overrideOverlayDialog.selectedSet
                    if (selected) {
                        if (selected.id === "__reset_all__") {
                            backend.resetOverlays()
                        } else {
                            var layered = selected.layeredPackages || []
                            var local = selected.localPackages || []
                            var removed = selected.removedPackages || []
                            backend.applyOverlaySet(layered, local, removed)
                        }
                    }
                    overrideOverlayDialog.close()
                }
            },
            Kirigami.Action {
                text: qsTr("Cancel")
                icon.name: "dialog-cancel"
                onTriggered: overrideOverlayDialog.close()
            }
        ]

        ColumnLayout {
            spacing: Kirigami.Units.mediumSpacing

            Controls.Label {
                text: qsTr("Select an Overlay Set to apply package modifications directly to the system, or remove all overlays to start fresh:")
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Controls.ComboBox {
                id: overrideCombo
                model: overrideOverlayDialog.overlayChoices
                textRole: "name"
                valueRole: "id"
                Layout.fillWidth: true
            }

            // Summary Preview (Layered, Local, and Removed Packages)
            ColumnLayout {
                spacing: Kirigami.Units.smallSpacing
                visible: overrideOverlayDialog.selectedSet !== null
                Layout.fillWidth: true

                Controls.Label {
                    text: overrideOverlayDialog.isResetSelection
                          ? qsTr("Start Fresh:")
                          : qsTr("Package Layer Preview:")
                    font.bold: true
                }

                Controls.Label {
                    visible: overrideOverlayDialog.isResetSelection
                    text: qsTr("This runs rpm-ostree reset: all layered packages, local packages, and package overrides will be removed, returning to the pure base image.")
                    wrapMode: Text.WordWrap
                    color: Kirigami.Theme.negativeTextColor
                    Layout.fillWidth: true
                }

                // Layered Packages Preview
                ColumnLayout {
                    spacing: 2
                    visible: !overrideOverlayDialog.isResetSelection && (overrideOverlayDialog.selectedSet && overrideOverlayDialog.selectedSet.layeredPackages || []).length > 0
                    Controls.Label {
                        text: qsTr("Layered Packages:")
                        font.pixelSize: Kirigami.Units.gridUnit * 0.7
                        color: Kirigami.Theme.disabledTextColor
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing
                        Repeater {
                            model: (overrideOverlayDialog.selectedSet && overrideOverlayDialog.selectedSet.layeredPackages) || []
                            delegate: Rectangle {
                                implicitWidth: oLPkgLabel.implicitWidth + 12
                                implicitHeight: oLPkgLabel.implicitHeight + 6
                                radius: 4
                                color: Qt.alpha(Kirigami.Theme.highlightColor, 0.15)
                                border.color: Kirigami.Theme.highlightColor
                                border.width: 1
                                Controls.Label {
                                    id: oLPkgLabel
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.pixelSize: Kirigami.Units.gridUnit * 0.75
                                }
                            }
                        }
                    }
                }

                // Local Packages Preview
                ColumnLayout {
                    spacing: 2
                    visible: !overrideOverlayDialog.isResetSelection && (overrideOverlayDialog.selectedSet && overrideOverlayDialog.selectedSet.localPackages || []).length > 0
                    Controls.Label {
                        text: qsTr("Local Packages:")
                        font.pixelSize: Kirigami.Units.gridUnit * 0.7
                        color: Kirigami.Theme.disabledTextColor
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing
                        Repeater {
                            model: (overrideOverlayDialog.selectedSet && overrideOverlayDialog.selectedSet.localPackages) || []
                            delegate: Rectangle {
                                implicitWidth: oLocPkgLabel.implicitWidth + 12
                                implicitHeight: oLocPkgLabel.implicitHeight + 6
                                radius: 4
                                color: Qt.alpha(Kirigami.Theme.positiveTextColor, 0.15)
                                border.color: Kirigami.Theme.positiveTextColor
                                border.width: 1
                                Controls.Label {
                                    id: oLocPkgLabel
                                    anchors.centerIn: parent
                                    text: formatPackageName(modelData)
                                    font.pixelSize: Kirigami.Units.gridUnit * 0.75
                                }

                                Controls.ToolTip.visible: (modelData || "").indexOf("/") !== -1 && oLocMouse.containsMouse
                                Controls.ToolTip.text: modelData

                                MouseArea {
                                    id: oLocMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                }
                            }
                        }
                    }
                }

                // Removed Packages Preview
                ColumnLayout {
                    spacing: 2
                    visible: !overrideOverlayDialog.isResetSelection && (overrideOverlayDialog.selectedSet && overrideOverlayDialog.selectedSet.removedPackages || []).length > 0
                    Controls.Label {
                        text: qsTr("Removed Packages:")
                        font.pixelSize: Kirigami.Units.gridUnit * 0.7
                        color: Kirigami.Theme.disabledTextColor
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing
                        Repeater {
                            model: (overrideOverlayDialog.selectedSet && overrideOverlayDialog.selectedSet.removedPackages) || []
                            delegate: Rectangle {
                                implicitWidth: oRemPkgLabel.implicitWidth + 12
                                implicitHeight: oRemPkgLabel.implicitHeight + 6
                                radius: 4
                                color: Qt.alpha(Kirigami.Theme.negativeTextColor, 0.15)
                                border.color: Kirigami.Theme.negativeTextColor
                                border.width: 1
                                Controls.Label {
                                    id: oRemPkgLabel
                                    anchors.centerIn: parent
                                    text: modelData
                                    font.pixelSize: Kirigami.Units.gridUnit * 0.75
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
