import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: qsTr("Overlay Sets")
    footer: StatusBar {}

    actions: [
        Kirigami.Action {
            text: qsTr("Create Overlay Set")
            icon.name: "list-add"
            onTriggered: {
                currentEditId = ""
                editNameInput.text = ""
                editDescInput.text = ""
                editLayeredList = []
                editLocalList = []
                editRemovedList = []
                editDialog.title = qsTr("Create Overlay Set")
                editDialog.open()
            }
        },
        Kirigami.Action {
            text: qsTr("Export All JSON")
            icon.name: "document-export"
            onTriggered: {
                jsonTextDialog.title = qsTr("Export Overlay Sets JSON")
                jsonArea.text = overlayService.exportJson()
                jsonArea.readOnly = true
                jsonTextDialog.isImportMode = false
                jsonTextDialog.open()
            }
        },
        Kirigami.Action {
            text: qsTr("Import JSON")
            icon.name: "document-import"
            onTriggered: {
                jsonTextDialog.title = qsTr("Import Overlay Sets JSON")
                jsonArea.text = ""
                jsonArea.readOnly = false
                jsonTextDialog.isImportMode = true
                jsonTextDialog.open()
            }
        }
    ]

    property string currentEditId: ""
    property var editLayeredList: []
    property var editLocalList: []
    property var editRemovedList: []
    property var searchResultsModel: []

    function formatPackageName(str) {
        if (!str) return ""
        var s = str.toString().trim()
        var idx = s.lastIndexOf("/")
        if (idx !== -1) {
            s = s.substring(idx + 1)
        }
        return s
    }

    function addCurrentPackage() {
        var name = addPkgInput.text.trim()
        if (name === "") return
        var catIndex = categoryCombo.currentIndex
        if (catIndex === 0) {
            var arr = page.editLayeredList ? page.editLayeredList.slice() : []
            if (arr.indexOf(name) === -1) {
                arr.push(name)
            }
            page.editLayeredList = arr
        } else if (catIndex === 1) {
            var arr2 = page.editLocalList ? page.editLocalList.slice() : []
            if (arr2.indexOf(name) === -1) {
                arr2.push(name)
            }
            page.editLocalList = arr2
        } else if (catIndex === 2) {
            var arr3 = page.editRemovedList ? page.editRemovedList.slice() : []
            if (arr3.indexOf(name) === -1) {
                arr3.push(name)
            }
            page.editRemovedList = arr3
        }
        addPkgInput.text = ""
        if (typeof autocompletePopup !== "undefined") {
            autocompletePopup.close()
        }
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing
        width: page.width

        // Search Filter
        Kirigami.SearchField {
            id: searchField
            Layout.fillWidth: true
            placeholderText: qsTr("Filter overlay sets...")
        }

        // Empty State
        Controls.Label {
            visible: overlaySetsRepeater.count === 0
            text: qsTr("No overlay sets saved yet. Click 'Create Overlay Set' or save your current system state from the Deployments page.")
            wrapMode: Text.WordWrap
            font.italic: true
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
        }

        // Overlay Set Cards
        Repeater {
            id: overlaySetsRepeater
            model: {
                var allSets = overlayService.overlaySets || []
                var query = searchField.text.trim().toLowerCase()
                if (query === "") return allSets
                return allSets.filter(function(s) {
                    return (s.name || "").toLowerCase().indexOf(query) !== -1 ||
                           (s.description || "").toLowerCase().indexOf(query) !== -1
                })
            }

            delegate: Kirigami.Card {
                id: setCard
                Layout.fillWidth: true

                header: RowLayout {
                    spacing: Kirigami.Units.mediumSpacing

                    Kirigami.Heading {
                        text: modelData.name || qsTr("Unnamed Set")
                        level: 2
                        Layout.fillWidth: true
                    }

                    Controls.Button {
                        icon.name: "edit-entry"
                        text: qsTr("Edit")
                        onClicked: {
                            currentEditId = modelData.id || ""
                            editNameInput.text = modelData.name || ""
                            editDescInput.text = modelData.description || ""
                            editLayeredList = (modelData.layeredPackages || []).slice()
                            editLocalList = (modelData.localPackages || []).slice()
                            editRemovedList = (modelData.removedPackages || []).slice()
                            editDialog.title = qsTr("Edit Overlay Set")
                            editDialog.open()
                        }
                    }

                    Controls.Button {
                        icon.name: "dialog-ok-apply"
                        text: qsTr("Apply")
                        enabled: !backend.transactionInProgress
                        onClicked: {
                            backend.applyOverlaySet(
                                modelData.layeredPackages || [],
                                modelData.localPackages || [],
                                modelData.removedPackages || []
                            )
                        }
                    }

                    Controls.Button {
                        icon.name: "edit-copy"
                        text: qsTr("Duplicate")
                        onClicked: {
                            overlayService.createOverlaySet(
                                (modelData.name || "") + " (Copy)",
                                modelData.description || "",
                                modelData.layeredPackages || [],
                                modelData.localPackages || [],
                                modelData.removedPackages || []
                            )
                        }
                    }

                    Controls.Button {
                        icon.name: "edit-delete"
                        text: qsTr("Delete")
                        onClicked: deleteConfirmDialog.openWithId(modelData.id, modelData.name)
                    }
                }

                contentItem: ColumnLayout {
                    spacing: Kirigami.Units.mediumSpacing

                    Controls.Label {
                        visible: (modelData.description || "") !== ""
                        text: modelData.description || ""
                        wrapMode: Text.WordWrap
                        color: Kirigami.Theme.disabledTextColor
                        Layout.fillWidth: true
                    }

                    // Layered Packages Badge Flow
                    ColumnLayout {
                        spacing: Kirigami.Units.smallSpacing
                        visible: (modelData.layeredPackages || []).length > 0
                        Layout.fillWidth: true

                        Controls.Label {
                            text: qsTr("Layered Packages (%1):").arg(modelData.layeredPackages.length)
                            font.bold: true
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Repeater {
                                model: modelData.layeredPackages || []
                                delegate: Rectangle {
                                    implicitWidth: lPkgLabel.implicitWidth + 12
                                    implicitHeight: lPkgLabel.implicitHeight + 6
                                    radius: 4
                                    color: Qt.alpha(Kirigami.Theme.highlightColor, 0.15)
                                    border.color: Kirigami.Theme.highlightColor
                                    border.width: 1

                                    Controls.Label {
                                        id: lPkgLabel
                                        anchors.centerIn: parent
                                        text: modelData
                                        font.pixelSize: Kirigami.Units.gridUnit * 0.75
                                    }
                                }
                            }
                        }
                    }

                    // Local Packages Badge Flow
                    ColumnLayout {
                        spacing: Kirigami.Units.smallSpacing
                        visible: (modelData.localPackages || []).length > 0
                        Layout.fillWidth: true

                        Controls.Label {
                            text: qsTr("Local Packages (%1):").arg(modelData.localPackages.length)
                            font.bold: true
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Repeater {
                                model: modelData.localPackages || []
                                delegate: Rectangle {
                                    implicitWidth: locPkgLabel.implicitWidth + 12
                                    implicitHeight: locPkgLabel.implicitHeight + 6
                                    radius: 4
                                    color: Qt.alpha(Kirigami.Theme.positiveTextColor, 0.15)
                                    border.color: Kirigami.Theme.positiveTextColor
                                    border.width: 1

                                    Controls.Label {
                                        id: locPkgLabel
                                        anchors.centerIn: parent
                                        text: page.formatPackageName(modelData)
                                        font.pixelSize: Kirigami.Units.gridUnit * 0.75
                                    }

                                    Controls.ToolTip.visible: (modelData || "").indexOf("/") !== -1 && setLocMouse.containsMouse
                                    Controls.ToolTip.text: modelData

                                    MouseArea {
                                        id: setLocMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                    }
                                }
                            }
                        }
                    }

                    // Removed Packages Badge Flow
                    ColumnLayout {
                        spacing: Kirigami.Units.smallSpacing
                        visible: (modelData.removedPackages || []).length > 0
                        Layout.fillWidth: true

                        Controls.Label {
                            text: qsTr("Removed Packages (%1):").arg(modelData.removedPackages.length)
                            font.bold: true
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing

                            Repeater {
                                model: modelData.removedPackages || []
                                delegate: Rectangle {
                                    implicitWidth: rPkgLabel.implicitWidth + 12
                                    implicitHeight: rPkgLabel.implicitHeight + 6
                                    radius: 4
                                    color: Qt.alpha(Kirigami.Theme.negativeTextColor, 0.15)
                                    border.color: Kirigami.Theme.negativeTextColor
                                    border.width: 1

                                    Controls.Label {
                                        id: rPkgLabel
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

    // Edit/Create Dialog
    Kirigami.Dialog {
        id: editDialog
        title: qsTr("Edit Overlay Set")
        padding: Kirigami.Units.largeSpacing
        preferredWidth: Kirigami.Units.gridUnit * 30

        customFooterActions: [
            Kirigami.Action {
                text: qsTr("Save Overlay Set")
                icon.name: "document-save"
                onTriggered: {
                    if (currentEditId === "") {
                        overlayService.createOverlaySet(
                            editNameInput.text,
                            editDescInput.text,
                            editLayeredList,
                            editLocalList,
                            editRemovedList
                        )
                    } else {
                        overlayService.updateOverlaySet(
                            currentEditId,
                            editNameInput.text,
                            editDescInput.text,
                            editLayeredList,
                            editLocalList,
                            editRemovedList
                        )
                    }
                    editDialog.close()
                }
            },
            Kirigami.Action {
                text: qsTr("Cancel")
                icon.name: "dialog-cancel"
                onTriggered: editDialog.close()
            }
        ]

        ColumnLayout {
            spacing: Kirigami.Units.mediumSpacing

            Kirigami.FormLayout {
                Layout.fillWidth: true

                Controls.TextField {
                    id: editNameInput
                    Kirigami.FormData.label: qsTr("Profile Name:")
                    placeholderText: "Gaming & Development Stack"
                    Layout.fillWidth: true
                }

                Controls.TextField {
                    id: editDescInput
                    Kirigami.FormData.label: qsTr("Description:")
                    placeholderText: "Custom packages for gaming and dev"
                    Layout.fillWidth: true
                }
            }

            // Package Category Tabs / Sections
            Controls.Label {
                text: qsTr("Manage Package Lists:")
                font.bold: true
            }

            // Add Package Field with Autocomplete
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                RowLayout {
                    Layout.fillWidth: true

                    Controls.ComboBox {
                        id: categoryCombo
                        model: [qsTr("Layered Package"), qsTr("Local Package"), qsTr("Removed Package")]
                    }

                    Controls.TextField {
                        id: addPkgInput
                        placeholderText: categoryCombo.currentIndex === 1 ? qsTr("Path to local .rpm file...") : qsTr("Type package name (autocomplete available)...")
                        Layout.fillWidth: true
                        onTextChanged: {
                            if (text.trim().length >= 1 && categoryCombo.currentIndex !== 1) {
                                searchTimer.restart()
                            } else {
                                autocompletePopup.close()
                            }
                        }
                        onAccepted: {
                            page.addCurrentPackage()
                        }
                    }

                    Controls.Button {
                        text: qsTr("Browse...")
                        icon.name: "document-open"
                        visible: categoryCombo.currentIndex === 1
                        onClicked: localRpmFileDialog.open()
                    }

                    Controls.Button {
                        text: qsTr("Add")
                        icon.name: "list-add"
                        onClicked: page.addCurrentPackage()
                    }
                }

                // File Dialog for Local .rpm files
                FileDialog {
                    id: localRpmFileDialog
                    title: qsTr("Select Local RPM Package File")
                    nameFilters: [qsTr("RPM Package Files (*.rpm)"), qsTr("All Files (*)")]
                    onAccepted: {
                        var path = localRpmFileDialog.selectedFile.toString()
                        if (path.startsWith("file://")) {
                            path = path.substring(7)
                        }
                        addPkgInput.text = path
                        page.addCurrentPackage()
                    }
                }

                // Search Autocomplete Popup
                Controls.Popup {
                    id: autocompletePopup
                    parent: addPkgInput
                    y: addPkgInput.height
                    x: 0
                    width: addPkgInput.width
                    height: Math.min(200, autocompleteList.contentHeight + 16)
                    padding: 4
                    focus: false

                    contentItem: ListView {
                        id: autocompleteList
                        model: page.searchResultsModel
                        clip: true

                        delegate: Controls.ItemDelegate {
                            width: autocompleteList.width
                            contentItem: ColumnLayout {
                                spacing: 2
                                Controls.Label {
                                    text: modelData.name || ""
                                    font.bold: true
                                }
                                Controls.Label {
                                    text: modelData.summary ? (modelData.summary + (modelData.version ? (" (" + modelData.version + ")") : "")) : ""
                                    font.pixelSize: Kirigami.Units.gridUnit * 0.7
                                    color: Kirigami.Theme.disabledTextColor
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                            }
                            onClicked: {
                                addPkgInput.text = modelData.name || ""
                                autocompletePopup.close()
                                page.addCurrentPackage()
                            }
                        }
                    }
                }

                Timer {
                    id: searchTimer
                    interval: 200
                    repeat: false
                    onTriggered: {
                        var query = addPkgInput.text.trim()
                        if (query.length === 0) {
                            page.searchResultsModel = []
                            autocompletePopup.close()
                            return
                        }

                        var catIndex = categoryCombo.currentIndex
                        if (catIndex === 2) {
                            // Removed Package: filter installed deployment packages first
                            var installed = backend.getDeploymentPackages() || []
                            var filtered = []
                            var lower = query.toLowerCase()
                            for (var i = 0; i < installed.length; ++i) {
                                if (installed[i].toLowerCase().indexOf(lower) !== -1) {
                                    filtered.push({ name: installed[i], summary: qsTr("Installed in current deployment"), version: "" })
                                }
                            }
                            var remote = backend.searchPackages(query) || []
                            for (var j = 0; j < remote.length; ++j) {
                                var rName = remote[j].name || ""
                                var exists = false
                                for (var k = 0; k < filtered.length; ++k) {
                                    if (filtered[k].name === rName) { exists = true; break; }
                                }
                                if (!exists) filtered.push(remote[j])
                            }
                            page.searchResultsModel = filtered
                            if (filtered.length > 0) autocompletePopup.open()
                            else autocompletePopup.close()
                        } else if (catIndex === 0) {
                            var res = backend.searchPackages(query) || []
                            page.searchResultsModel = res
                            if (res.length > 0) autocompletePopup.open()
                            else autocompletePopup.close()
                        }
                    }
                }
            }

            // Interactive Badges for Layered Packages
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Controls.Label {
                    text: qsTr("Layered Packages:")
                    font.bold: true
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Repeater {
                        model: page.editLayeredList
                        delegate: Rectangle {
                            implicitWidth: eLPkgRow.implicitWidth + 12
                            implicitHeight: eLPkgRow.implicitHeight + 6
                            radius: 4
                            color: Qt.alpha(Kirigami.Theme.highlightColor, 0.15)
                            border.color: Kirigami.Theme.highlightColor
                            border.width: 1

                            RowLayout {
                                id: eLPkgRow
                                anchors.centerIn: parent
                                spacing: 4

                                Controls.Label {
                                    text: modelData
                                    font.pixelSize: Kirigami.Units.gridUnit * 0.75
                                }

                                Controls.ToolButton {
                                    icon.name: "edit-delete"
                                    implicitWidth: 16
                                    implicitHeight: 16
                                    onClicked: {
                                        var arr = (page.editLayeredList || []).slice()
                                        arr.splice(index, 1)
                                        page.editLayeredList = arr
                                    }
                                }
                            }
                        }
                    }

                    Controls.Label {
                        visible: !(page.editLayeredList) || page.editLayeredList.length === 0
                        text: qsTr("No layered packages specified.")
                        font.italic: true
                        color: Kirigami.Theme.disabledTextColor
                    }
                }
            }

            // Interactive Badges for Local Packages
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Controls.Label {
                    text: qsTr("Local Packages:")
                    font.bold: true
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Repeater {
                        model: page.editLocalList
                        delegate: Rectangle {
                            implicitWidth: eLocPkgRow.implicitWidth + 12
                            implicitHeight: eLocPkgRow.implicitHeight + 6
                            radius: 4
                            color: Qt.alpha(Kirigami.Theme.positiveTextColor, 0.15)
                            border.color: Kirigami.Theme.positiveTextColor
                            border.width: 1

                            RowLayout {
                                id: eLocPkgRow
                                anchors.centerIn: parent
                                spacing: 4

                                Controls.Label {
                                    text: page.formatPackageName(modelData)
                                    font.pixelSize: Kirigami.Units.gridUnit * 0.75
                                }

                                Controls.ToolTip.visible: (modelData || "").indexOf("/") !== -1 && eLocMouse.containsMouse
                                Controls.ToolTip.text: modelData

                                MouseArea {
                                    id: eLocMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                }

                                Controls.ToolButton {
                                    icon.name: "edit-delete"
                                    implicitWidth: 16
                                    implicitHeight: 16
                                    onClicked: {
                                        var arr = (page.editLocalList || []).slice()
                                        arr.splice(index, 1)
                                        page.editLocalList = arr
                                    }
                                }
                            }
                        }
                    }

                    Controls.Label {
                        visible: !(page.editLocalList) || page.editLocalList.length === 0
                        text: qsTr("No local packages specified.")
                        font.italic: true
                        color: Kirigami.Theme.disabledTextColor
                    }
                }
            }

            // Interactive Badges for Removed Packages
            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing

                Controls.Label {
                    text: qsTr("Removed Packages:")
                    font.bold: true
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing

                    Repeater {
                        model: page.editRemovedList
                        delegate: Rectangle {
                            implicitWidth: eRPkgRow.implicitWidth + 12
                            implicitHeight: eRPkgRow.implicitHeight + 6
                            radius: 4
                            color: Qt.alpha(Kirigami.Theme.negativeTextColor, 0.15)
                            border.color: Kirigami.Theme.negativeTextColor
                            border.width: 1

                            RowLayout {
                                id: eRPkgRow
                                anchors.centerIn: parent
                                spacing: 4

                                Controls.Label {
                                    text: modelData
                                    font.pixelSize: Kirigami.Units.gridUnit * 0.75
                                }

                                Controls.ToolButton {
                                    icon.name: "edit-delete"
                                    implicitWidth: 16
                                    implicitHeight: 16
                                    onClicked: {
                                        var arr = (page.editRemovedList || []).slice()
                                        arr.splice(index, 1)
                                        page.editRemovedList = arr
                                    }
                                }
                            }
                        }
                    }

                    Controls.Label {
                        visible: !(page.editRemovedList) || page.editRemovedList.length === 0
                        text: qsTr("No removed packages specified.")
                        font.italic: true
                        color: Kirigami.Theme.disabledTextColor
                    }
                }
            }
        }
    }

    // Delete Confirmation Dialog
    Kirigami.Dialog {
        id: deleteConfirmDialog
        title: qsTr("Confirm Delete Overlay Set")
        padding: Kirigami.Units.largeSpacing

        property string deleteTargetId: ""
        property string deleteTargetName: ""

        function openWithId(id, name) {
            deleteConfirmDialog.deleteTargetId = id
            deleteConfirmDialog.deleteTargetName = name
            deleteConfirmDialog.open()
        }

        customFooterActions: [
            Kirigami.Action {
                text: qsTr("Delete Overlay Set")
                icon.name: "edit-delete"
                onTriggered: {
                    overlayService.deleteOverlaySet(deleteConfirmDialog.deleteTargetId)
                    deleteConfirmDialog.close()
                }
            },
            Kirigami.Action {
                text: qsTr("Cancel")
                icon.name: "dialog-cancel"
                onTriggered: deleteConfirmDialog.close()
            }
        ]

        Controls.Label {
            text: qsTr("Are you sure you want to delete the overlay set '%1'?").arg(deleteConfirmDialog.deleteTargetName)
            wrapMode: Text.WordWrap
            Layout.fillWidth: true
        }
    }

    // JSON Import/Export Dialog
    Kirigami.Dialog {
        id: jsonTextDialog
        title: qsTr("Overlay Sets JSON")
        padding: Kirigami.Units.largeSpacing
        preferredWidth: Kirigami.Units.gridUnit * 30

        property bool isImportMode: false

        customFooterActions: [
            Kirigami.Action {
                text: jsonTextDialog.isImportMode ? qsTr("Import") : qsTr("Close")
                icon.name: jsonTextDialog.isImportMode ? "document-import" : "dialog-close"
                onTriggered: {
                    if (jsonTextDialog.isImportMode) {
                        overlayService.importJson(jsonArea.text)
                    }
                    jsonTextDialog.close()
                }
            }
        ]

        ColumnLayout {
            spacing: Kirigami.Units.mediumSpacing

            Controls.TextArea {
                id: jsonArea
                font.family: "Monospace"
                Layout.fillWidth: true
                implicitHeight: 250
                wrapMode: Text.NoWrap
            }
        }
    }
}
