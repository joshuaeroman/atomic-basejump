import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: qsTr("OS Image Browser")
    footer: StatusBar {}
    // Content is taller than the viewport, so the vertical scrollbar appears
    // when the page is shown. Keep it permanent so the viewport width never
    // changes after show (a transient scrollbar reflows the cards ~21px).
    verticalScrollBarPolicy: Controls.ScrollBar.AlwaysOn

    function formatPackageName(str) {
        if (!str) return ""
        var s = str.toString().trim()
        var idx = s.lastIndexOf("/")
        if (idx !== -1) {
            s = s.substring(idx + 1)
        }
        return s
    }

    property var sourcesList: imageRegistry.sources()
    property int selectedSourceIndex: 0
    property string currentSourceId: sourcesList.length > 0 ? sourcesList[selectedSourceIndex]["id"] : "fedora"

    property var typesList: imageRegistry.typesForSource(currentSourceId)
    property int selectedTypeIndex: 0
    property var currentTypeObj: typesList.length > selectedTypeIndex ? typesList[selectedTypeIndex] : ({})
    property string currentImageRef: currentTypeObj.imageRef || ""

    property var availableStreams: ["latest", "stable", "beta", "testing"]
    property int selectedStreamIndex: 0
    property string currentStream: availableStreams.length > selectedStreamIndex ? availableStreams[selectedStreamIndex] : "latest"

    property var availableVersions: ["latest", "44", "43", "42"]
    property int selectedVersionIndex: 0
    property string currentVersion: availableVersions.length > selectedVersionIndex ? availableVersions[selectedVersionIndex] : "latest"

    // Modes for tag selection: Use Stream or Use Specific Version
    property bool useVersionTag: false
    property string selectedTag: useVersionTag ? currentVersion : currentStream
    property string selectedTagBuildDate: ""

    onSelectedTagChanged: {
        page.selectedTagBuildDate = ""
        if (page.currentImageRef !== "" && page.selectedTag !== "") {
            imageRegistry.fetchTagBuildDate(page.currentImageRef, page.selectedTag)
        }
    }

    // Booted image transport / vendor (for uBlue signed vs unsigned defaults)
    property string bootedImageRef: {
        var d = backend.bootedDeployment || {}
        return d["container-image-reference"] || d["origin"] || ""
    }
    property bool bootedIsUblue: imageRegistry.isUblueRef(bootedImageRef)
    property bool bootedIsSigned: imageRegistry.isSignedTransport(bootedImageRef)
    property bool allowSignedUblue: imageRegistry.allowsSignedUblueTarget(bootedImageRef)

    // Signature mode: only meaningful for uBlue (and other supportsSignatureChoice types).
    // Non-uBlue sources always use signed transport (ostree-image-signed).
    property bool targetIsUblue: imageRegistry.isUblueRef(currentImageRef)
    property bool requireSignature: {
        if (!targetIsUblue) {
            return true
        }
        // Default: signed only when already on signed uBlue
        return imageRegistry.preferSignedDefault(bootedImageRef)
    }
    // User override after load / source changes — kept in sync via applySignatureDefault()
    property bool userRequireSignature: requireSignature

    property bool signatureChoiceVisible: currentSourceId === "ublue" || !!(currentTypeObj && currentTypeObj.supportsSignatureChoice)

    property string fullRefSpec: {
        if (currentImageRef === "")
            return ""
        var signed = signatureChoiceVisible ? userRequireSignature : true
        // Never emit a signed uBlue target when the base is non-uBlue
        if (targetIsUblue && signed && !allowSignedUblue) {
            signed = false
        }
        return imageRegistry.constructRefSpec(currentImageRef, selectedTag, signed)
    }

    // True when the user asked for signed uBlue but the booted base is non-uBlue
    // (refspec is coerced to unsigned; signed radio is disabled).
    property bool signedUblueUnavailable: targetIsUblue && !allowSignedUblue
    property var selectedOverlaySet: null

    // DE-family switch: Plasma Login Manager prep (GNOME → Plasma black-screen guard)
    property string bootedDesktopFamily: backend.bootedDesktopFamily || "unknown"
    property string targetDesktopFamily: imageRegistry.desktopFamilyFromRef(currentImageRef || fullRefSpec)
    property bool showPlasmaLoginPrep: {
        // Depend on booted family so the binding refreshes after status loads.
        var _ = page.bootedDesktopFamily
        return backend.needsPlasmaLoginPrep(page.fullRefSpec)
    }
    property bool prepPlasmaLogin: true

    onShowPlasmaLoginPrepChanged: {
        if (showPlasmaLoginPrep)
            prepPlasmaLogin = true
    }

    // Pre-select booted image once on load (do not override later user changes)
    property string preferredTag: ""
    property bool appliedBootedSelection: false
    property bool applyingBootedSelection: false

    function applySignatureDefault() {
        if (!signatureChoiceVisible) {
            userRequireSignature = true
            return
        }
        if (imageRegistry.preferSignedDefault(bootedImageRef) && allowSignedUblue) {
            userRequireSignature = true
        } else {
            userRequireSignature = false
        }
    }

    function toStringList(list) {
        var out = []
        if (!list)
            return out
        for (var i = 0; i < list.length; ++i)
            out.push(String(list[i]))
        return out
    }

    function indexOfTag(list, tag) {
        if (!list || !tag)
            return -1
        var needle = String(tag)
        for (var i = 0; i < list.length; ++i) {
            if (list[i] === needle)
                return i
        }
        var lower = needle.toLowerCase()
        for (var j = 0; j < list.length; ++j) {
            if (String(list[j]).toLowerCase() === lower)
                return j
        }
        return -1
    }

    function defaultTagIndex(list) {
        var latest = page.indexOfTag(list, "latest")
        return latest >= 0 ? latest : 0
    }

    function selectPreferredTag(streams, versions) {
        var tag = page.preferredTag
        if (!tag || tag.length === 0) {
            page.selectedStreamIndex = page.defaultTagIndex(streams)
            page.selectedVersionIndex = 0
            return
        }

        var sList = page.toStringList(streams)
        var vList = page.toStringList(versions)

        if (page.useVersionTag) {
            var vIdx = page.indexOfTag(vList, tag)
            if (vIdx < 0) {
                // Try major version (e.g. "42.20250101" → "42")
                var major = String(tag).split(/[.\-]/)[0]
                if (major && major !== tag)
                    vIdx = page.indexOfTag(vList, major)
            }
            if (vIdx < 0) {
                vList.unshift(tag)
                vIdx = 0
            }
            page.availableVersions = vList
            page.selectedVersionIndex = vIdx
            if (sList.length > 0) {
                page.availableStreams = sList
                page.selectedStreamIndex = 0
            }
        } else {
            var sIdx = page.indexOfTag(sList, tag)
            if (sIdx < 0) {
                sList.unshift(tag)
                sIdx = 0
            }
            page.availableStreams = sList
            page.selectedStreamIndex = sIdx
            if (vList.length > 0) {
                page.availableVersions = vList
                page.selectedVersionIndex = 0
            }
        }
        page.preferredTag = ""
    }

    function applyBootedSelection() {
        if (page.appliedBootedSelection)
            return
        var ref = page.bootedImageRef
        if (!ref || ref.length === 0)
            return

        var sel = imageRegistry.resolveBootedSelection(ref)
        if (!sel || !sel.found) {
            page.appliedBootedSelection = true
            page.applySignatureDefault()
            if (page.currentImageRef !== "")
                imageRegistry.fetchTags(page.currentImageRef)
            return
        }

        page.applyingBootedSelection = true
        page.selectedSourceIndex = sel.sourceIndex
        page.currentSourceId = sel.sourceId
        page.typesList = imageRegistry.typesForSource(page.currentSourceId)
        page.selectedTypeIndex = sel.typeIndex
        if (page.typesList.length > sel.typeIndex) {
            page.currentTypeObj = page.typesList[sel.typeIndex]
            page.currentImageRef = page.currentTypeObj.imageRef || sel.imageRef || ""
        } else {
            page.currentImageRef = sel.imageRef || ""
        }

        var tag = sel.tag || ""
        page.preferredTag = tag
        if (tag.length > 0)
            page.useVersionTag = !!sel.useVersionTag

        page.applyingBootedSelection = false
        page.appliedBootedSelection = true
        page.applySignatureDefault()
        if (page.currentImageRef !== "")
            imageRegistry.fetchTags(page.currentImageRef)
    }

    onCurrentSourceIdChanged: {
        if (page.applyingBootedSelection)
            return
        typesList = imageRegistry.typesForSource(currentSourceId)
        selectedTypeIndex = 0
        if (typesList.length > 0) {
            currentTypeObj = typesList[0]
            currentImageRef = typesList[0].imageRef
            imageRegistry.fetchTags(currentImageRef)
        }
        applySignatureDefault()
    }

    onSelectedTypeIndexChanged: {
        if (page.applyingBootedSelection)
            return
        if (typesList.length > selectedTypeIndex) {
            currentTypeObj = typesList[selectedTypeIndex]
            currentImageRef = currentTypeObj.imageRef || ""
            if (currentImageRef !== "") {
                imageRegistry.fetchTags(currentImageRef)
            }
        }
        applySignatureDefault()
    }

    onBootedImageRefChanged: {
        if (!page.appliedBootedSelection && page.bootedImageRef !== "")
            page.applyBootedSelection()
        else
            page.applySignatureDefault()
    }

    Component.onCompleted: {
        page.applyBootedSelection()
        if (!page.appliedBootedSelection) {
            page.applySignatureDefault()
            if (page.currentImageRef !== "")
                imageRegistry.fetchTags(page.currentImageRef)
        }
    }

    Connections {
        target: imageRegistry
        function onTagsFetched(imageRef, streams, versions, allTags) {
            if (imageRef === page.currentImageRef) {
                if (page.preferredTag && page.preferredTag.length > 0) {
                    if (streams && streams.length > 0)
                        page.availableStreams = streams
                    if (versions && versions.length > 0)
                        page.availableVersions = versions
                    page.selectPreferredTag(streams, versions)
                } else {
                    if (streams && streams.length > 0) {
                        page.availableStreams = streams
                        page.selectedStreamIndex = page.defaultTagIndex(streams)
                    }
                    if (versions && versions.length > 0) {
                        page.availableVersions = versions
                        page.selectedVersionIndex = 0
                    }
                }
                if (page.currentImageRef !== "" && page.selectedTag !== "") {
                    imageRegistry.fetchTagBuildDate(page.currentImageRef, page.selectedTag)
                }
            }
        }

        function onTagBuildDateFetched(imageRef, tag, formattedDate) {
            if (imageRef === page.currentImageRef && tag === page.selectedTag) {
                page.selectedTagBuildDate = formattedDate
            }
        }

        function onFetchError(imageRef, error) {
            if (imageRef !== page.currentImageRef)
                return
            page.availableStreams = ["latest", "stable", "beta"]
            page.availableVersions = ["latest"]
            page.selectedStreamIndex = 0
            page.selectedVersionIndex = 0
        }
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing
        width: page.width

        // Header Description
        Kirigami.Card {
            Layout.fillWidth: true

            header: Kirigami.Heading {
                text: qsTr("Explore & Rebase Operating System Images")
                level: 2
            }

            contentItem: ColumnLayout {
                spacing: Kirigami.Units.smallSpacing

                Controls.Label {
                    text: qsTr("Browse containerized Linux OS images from official Fedora repositories, Universal Blue, and Secureblue. Select your preferred image variant, release stream, or OS version to stage a system rebase.")
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }
            }
        }

        // Selection Controls Form
        Kirigami.Card {
            Layout.fillWidth: true

            header: RowLayout {
                Kirigami.Heading {
                    text: qsTr("Image Configuration")
                    level: 3
                    Layout.fillWidth: true
                }
                Kirigami.Icon {
                    source: "system-search"
                    implicitWidth: Kirigami.Units.iconSizes.small
                    implicitHeight: Kirigami.Units.iconSizes.small
                }
            }

            contentItem: ColumnLayout {
                spacing: Kirigami.Units.mediumSpacing

                Kirigami.FormLayout {
                    Layout.fillWidth: true
                    // Desktop app: decide mode from available width, not content preferred width.
                    // Kirigami only updates wideImplicitWidth while wideMode is true, so a temporary
                    // width spike (e.g. uBlue signature row) can stick the form in narrow mode forever.
                    wideMode: width >= Kirigami.Units.gridUnit * 28

                    // 1. Image Source Selection
                    ColumnLayout {
                        Kirigami.FormData.label: qsTr("1. Image Source:")
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing

                        Controls.ComboBox {
                            id: sourceCombo
                            Layout.fillWidth: true
                            model: page.sourcesList
                            textRole: "name"
                            currentIndex: page.selectedSourceIndex
                            onActivated: index => {
                                page.selectedSourceIndex = index
                                page.currentSourceId = page.sourcesList[index]["id"]
                            }
                        }

                        Controls.Label {
                            text: page.sourcesList[page.selectedSourceIndex] ? page.sourcesList[page.selectedSourceIndex]["description"] : ""
                            font.italic: true
                            font.pixelSize: Kirigami.Units.gridUnit * 0.75
                            color: Kirigami.Theme.disabledTextColor
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            visible: text.length > 0
                        }
                    }

                    // 2. Image Type / Variant Selection
                    ColumnLayout {
                        Kirigami.FormData.label: qsTr("2. Image Variant / Type:")
                        Layout.fillWidth: true
                        spacing: Kirigami.Units.smallSpacing

                        Controls.ComboBox {
                            id: typeCombo
                            Layout.fillWidth: true
                            model: page.typesList
                            textRole: "name"
                            currentIndex: page.selectedTypeIndex
                            onActivated: index => {
                                page.selectedTypeIndex = index
                            }
                        }

                        Controls.Label {
                            text: page.currentTypeObj ? page.currentTypeObj["description"] || "" : ""
                            font.italic: true
                            font.pixelSize: Kirigami.Units.gridUnit * 0.75
                            color: Kirigami.Theme.disabledTextColor
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                            visible: text.length > 0
                        }
                    }

                    // 3. Signature transport (uBlue signed vs unsigned)
                    ColumnLayout {
                        Kirigami.FormData.label: qsTr("3. Signature:")
                        visible: page.signatureChoiceVisible
                        spacing: Kirigami.Units.smallSpacing
                        Layout.fillWidth: true

                        Flow {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.largeSpacing

                            Controls.RadioButton {
                                id: unsignedRadio
                                text: qsTr("Unsigned")
                                checked: !page.userRequireSignature
                                onToggled: if (checked) page.userRequireSignature = false
                            }
                            Controls.RadioButton {
                                id: signedRadio
                                text: qsTr("Signed")
                                checked: page.userRequireSignature
                                // Non-uBlue bases cannot jump to signed uBlue
                                enabled: page.allowSignedUblue
                                onToggled: {
                                    if (checked) {
                                        if (page.allowSignedUblue) {
                                            page.userRequireSignature = true
                                        } else {
                                            checked = false
                                            unsignedRadio.checked = true
                                            page.userRequireSignature = false
                                        }
                                    }
                                }
                            }
                        }

                        Controls.Label {
                            text: page.userRequireSignature
                                  ? qsTr("Transport: ostree-image-signed")
                                  : qsTr("Transport: ostree-unverified-registry")
                            font.family: "monospace"
                            font.pixelSize: Kirigami.Units.gridUnit * 0.7
                            color: Kirigami.Theme.disabledTextColor
                            elide: Text.ElideRight
                            Layout.fillWidth: true
                        }

                        Controls.Label {
                            visible: page.bootedIsUblue && page.bootedIsSigned
                            text: qsTr("On signed uBlue — defaulting to signed.")
                            font.italic: true
                            font.pixelSize: Kirigami.Units.gridUnit * 0.75
                            color: Kirigami.Theme.disabledTextColor
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        Controls.Label {
                            visible: !page.allowSignedUblue
                            text: qsTr("Signed disabled: not on a uBlue base. Rebase unsigned first.")
                            font.italic: true
                            font.pixelSize: Kirigami.Units.gridUnit * 0.75
                            color: Kirigami.Theme.neutralTextColor
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                        Controls.Label {
                            visible: page.bootedIsUblue && !page.bootedIsSigned
                            text: qsTr("On unsigned uBlue — defaulting to unsigned.")
                            font.italic: true
                            font.pixelSize: Kirigami.Units.gridUnit * 0.75
                            color: Kirigami.Theme.disabledTextColor
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    // Loading indicator for remote registry tags
                    RowLayout {
                        Kirigami.FormData.label: qsTr("Registry Tags:")
                        visible: imageRegistry.loadingTags
                        spacing: Kirigami.Units.smallSpacing
                        Layout.fillWidth: true

                        Controls.BusyIndicator {
                            running: imageRegistry.loadingTags
                            implicitWidth: Kirigami.Units.iconSizes.small
                            implicitHeight: Kirigami.Units.iconSizes.small
                        }
                        Controls.Label {
                            text: qsTr("Fetching available streams & versions from registry...")
                            color: Kirigami.Theme.disabledTextColor
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    // 4. Selection Mode: Stream vs Version
                    ColumnLayout {
                        Kirigami.FormData.label: qsTr("4. Tag Type:")
                        Layout.fillWidth: true

                        // Flow avoids a huge single-row implicit width from long radio labels
                        Flow {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.largeSpacing

                            Controls.RadioButton {
                                text: qsTr("Release Stream (e.g. stable, latest, beta)")
                                checked: !page.useVersionTag
                                onToggled: if (checked) page.useVersionTag = false
                            }
                            Controls.RadioButton {
                                text: qsTr("Specific Release / Version (e.g. 44, 43)")
                                checked: page.useVersionTag
                                onToggled: if (checked) page.useVersionTag = true
                            }
                        }
                    }

                    // 5. Stream or Version Dropdown
                    Controls.ComboBox {
                        id: streamCombo
                        visible: !page.useVersionTag
                        Kirigami.FormData.label: qsTr("5. Stream:")
                        Layout.fillWidth: true
                        model: page.availableStreams
                        currentIndex: page.selectedStreamIndex
                        onActivated: index => {
                            page.selectedStreamIndex = index
                        }
                    }

                    Controls.ComboBox {
                        id: versionCombo
                        visible: page.useVersionTag
                        Kirigami.FormData.label: qsTr("5. Version / Release Tag:")
                        Layout.fillWidth: true
                        model: page.availableVersions
                        currentIndex: page.selectedVersionIndex
                        onActivated: index => {
                            page.selectedVersionIndex = index
                        }
                    }

                    // Image Build Date Information
                    RowLayout {
                        Kirigami.FormData.label: qsTr("Build Date:")
                        visible: page.selectedTagBuildDate !== "" || imageRegistry.loadingBuildDate
                        spacing: Kirigami.Units.smallSpacing
                        Layout.fillWidth: true

                        Controls.BusyIndicator {
                            running: imageRegistry.loadingBuildDate
                            visible: imageRegistry.loadingBuildDate
                            implicitWidth: Kirigami.Units.iconSizes.small
                            implicitHeight: Kirigami.Units.iconSizes.small
                        }

                        Kirigami.Icon {
                            source: "clock"
                            visible: !imageRegistry.loadingBuildDate && page.selectedTagBuildDate !== ""
                            implicitWidth: Kirigami.Units.iconSizes.small
                            implicitHeight: Kirigami.Units.iconSizes.small
                        }

                        Controls.Label {
                            text: imageRegistry.loadingBuildDate
                                  ? qsTr("Fetching build timestamp from registry...")
                                  : page.selectedTagBuildDate
                            font.pixelSize: Kirigami.Units.gridUnit * 0.8
                            color: Kirigami.Theme.disabledTextColor
                            wrapMode: Text.WordWrap
                            Layout.fillWidth: true
                        }
                    }

                    // 6. Apply Overlay Set (Optional)
                    Controls.ComboBox {
                        id: overlaySetCombo
                        Kirigami.FormData.label: qsTr("6. Apply Overlay Set:")
                        model: {
                            var list = [
                                { name: qsTr("None (Keep current package layer)"), id: "" },
                                { name: qsTr("Remove all overlays (start fresh)"), id: "__reset_all__" }
                            ]
                            var saved = overlayService.overlaySets || []
                            for (var i = 0; i < saved.length; ++i) {
                                list.push(saved[i])
                            }
                            return list
                        }
                        textRole: "name"
                        valueRole: "id"
                        Layout.fillWidth: true
                        onCurrentIndexChanged: page.selectedOverlaySet = (currentIndex > 0 && model && model.length > currentIndex) ? model[currentIndex] : null
                    }
                }


                // Overlay Set Package Summary Preview (Layered, Local, and Removed)
                ColumnLayout {
                    spacing: Kirigami.Units.smallSpacing
                    visible: selectedOverlaySet !== null
                    Layout.fillWidth: true

                    Controls.Label {
                        text: selectedOverlaySet && selectedOverlaySet.id === "__reset_all__"
                              ? qsTr("Start Fresh:")
                              : qsTr("Selected Overlay Set Packages:")
                        font.bold: true
                    }

                    Controls.Label {
                        visible: selectedOverlaySet && selectedOverlaySet.id === "__reset_all__"
                        text: qsTr("All currently layered and local packages will be uninstalled during the rebase so the new image starts with a clean package layer.")
                        wrapMode: Text.WordWrap
                        color: Kirigami.Theme.negativeTextColor
                        Layout.fillWidth: true
                    }

                    // Layered Packages
                    ColumnLayout {
                        spacing: 2
                        visible: selectedOverlaySet && selectedOverlaySet.id !== "__reset_all__" && (selectedOverlaySet.layeredPackages || []).length > 0
                        Controls.Label {
                            text: qsTr("Layered Packages:")
                            font.pixelSize: Kirigami.Units.gridUnit * 0.7
                            color: Kirigami.Theme.disabledTextColor
                        }
                        Flow {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing
                            Repeater {
                                model: (selectedOverlaySet && selectedOverlaySet.layeredPackages) || []
                                delegate: Rectangle {
                                    implicitWidth: prevLPkgLabel.implicitWidth + 12
                                    implicitHeight: prevLPkgLabel.implicitHeight + 6
                                    radius: 4
                                    color: Qt.alpha(Kirigami.Theme.highlightColor, 0.15)
                                    border.color: Kirigami.Theme.highlightColor
                                    border.width: 1

                                    Controls.Label {
                                        id: prevLPkgLabel
                                        anchors.centerIn: parent
                                        text: modelData
                                        font.pixelSize: Kirigami.Units.gridUnit * 0.75
                                    }
                                }
                            }
                        }
                    }

                    // Local Packages
                    ColumnLayout {
                        spacing: 2
                        visible: selectedOverlaySet && selectedOverlaySet.id !== "__reset_all__" && (selectedOverlaySet.localPackages || []).length > 0
                        Controls.Label {
                            text: qsTr("Local Packages:")
                            font.pixelSize: Kirigami.Units.gridUnit * 0.7
                            color: Kirigami.Theme.disabledTextColor
                        }
                        Flow {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing
                            Repeater {
                                model: (selectedOverlaySet && selectedOverlaySet.localPackages) || []
                                delegate: Rectangle {
                                    implicitWidth: prevLocPkgLabel.implicitWidth + 12
                                    implicitHeight: prevLocPkgLabel.implicitHeight + 6
                                    radius: 4
                                    color: Qt.alpha(Kirigami.Theme.positiveTextColor, 0.15)
                                    border.color: Kirigami.Theme.positiveTextColor
                                    border.width: 1

                                    Controls.Label {
                                        id: prevLocPkgLabel
                                        anchors.centerIn: parent
                                        text: page.formatPackageName(modelData)
                                        font.pixelSize: Kirigami.Units.gridUnit * 0.75
                                    }

                                    Controls.ToolTip.visible: (modelData || "").indexOf("/") !== -1 && prevLocMouse.containsMouse
                                    Controls.ToolTip.text: modelData

                                    MouseArea {
                                        id: prevLocMouse
                                        anchors.fill: parent
                                        hoverEnabled: true
                                    }
                                }
                            }
                        }
                    }

                    // Removed Packages
                    ColumnLayout {
                        spacing: 2
                        visible: selectedOverlaySet && selectedOverlaySet.id !== "__reset_all__" && (selectedOverlaySet.removedPackages || []).length > 0
                        Controls.Label {
                            text: qsTr("Removed Packages:")
                            font.pixelSize: Kirigami.Units.gridUnit * 0.7
                            color: Kirigami.Theme.disabledTextColor
                        }
                        Flow {
                            Layout.fillWidth: true
                            spacing: Kirigami.Units.smallSpacing
                            Repeater {
                                model: (selectedOverlaySet && selectedOverlaySet.removedPackages) || []
                                delegate: Rectangle {
                                    implicitWidth: prevRPkgLabel.implicitWidth + 12
                                    implicitHeight: prevRPkgLabel.implicitHeight + 6
                                    radius: 4
                                    color: Qt.alpha(Kirigami.Theme.negativeTextColor, 0.15)
                                    border.color: Kirigami.Theme.negativeTextColor
                                    border.width: 1

                                    Controls.Label {
                                        id: prevRPkgLabel
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

        // Summary Card & Action Buttons
        Kirigami.Card {
            Layout.fillWidth: true

            header: Kirigami.Heading {
                text: qsTr("Selected Target Reference")
                level: 3
            }

            contentItem: ColumnLayout {
                spacing: Kirigami.Units.mediumSpacing

                Controls.TextField {
                    id: refOutput
                    text: page.fullRefSpec
                    readOnly: true
                    font.family: "monospace"
                    Layout.fillWidth: true
                    selectByMouse: true
                }

                RowLayout {
                    visible: page.selectedTagBuildDate !== "" || imageRegistry.loadingBuildDate
                    spacing: Kirigami.Units.smallSpacing
                    Layout.fillWidth: true

                    Kirigami.Icon {
                        source: "clock"
                        implicitWidth: Kirigami.Units.iconSizes.small
                        implicitHeight: Kirigami.Units.iconSizes.small
                    }

                    Controls.Label {
                        text: imageRegistry.loadingBuildDate
                              ? qsTr("Fetching build timestamp from registry...")
                              : qsTr("Image Build Date: %1").arg(page.selectedTagBuildDate)
                        font.pixelSize: Kirigami.Units.gridUnit * 0.8
                        color: Kirigami.Theme.disabledTextColor
                        wrapMode: Text.WordWrap
                        Layout.fillWidth: true
                    }
                }

                Kirigami.InlineMessage {
                    Layout.fillWidth: true
                    type: Kirigami.MessageType.Information
                    visible: page.signedUblueUnavailable
                    text: qsTr("Signed uBlue requires an existing uBlue base. Using unsigned transport for this rebase.")
                }

                // Conditional safety options (shown when a DE-family switch needs prep)
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.smallSpacing
                    visible: page.showPlasmaLoginPrep

                    Kirigami.InlineMessage {
                        Layout.fillWidth: true
                        type: Kirigami.MessageType.Warning
                        visible: true
                        text: qsTr("Desktop environment change: you are switching to a Plasma base. Preparing the Plasma login manager account is recommended so the login screen works after reboot.")
                    }

                    Controls.CheckBox {
                        id: prepPlasmaLoginCheck
                        checked: page.prepPlasmaLogin
                        text: qsTr("Prepare Plasma Login Manager accounts")
                        onToggled: page.prepPlasmaLogin = checked
                    }

                    Controls.Label {
                        text: qsTr("Ensures the login screen works after switching from a GNOME-family system. Safe to leave enabled.")
                        wrapMode: Text.WordWrap
                        color: Kirigami.Theme.disabledTextColor
                        Layout.fillWidth: true
                        leftPadding: prepPlasmaLoginCheck.indicator ? prepPlasmaLoginCheck.indicator.width + prepPlasmaLoginCheck.spacing : 0
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: Kirigami.Units.mediumSpacing

                    Controls.Button {
                        text: qsTr("Copy Reference")
                        icon.name: "edit-copy"
                        onClicked: {
                            refOutput.selectAll()
                            refOutput.copy()
                            copyBanner.open()
                        }
                    }

                    Item { Layout.fillWidth: true }

                    Controls.Button {
                        text: qsTr("Rebase System to Selected Image")
                        icon.name: "system-switch-user"
                        highlighted: true
                        enabled: page.fullRefSpec !== "" && !backend.transactionInProgress
                        onClicked: confirmDialog.open()
                    }
                }

                Kirigami.InlineMessage {
                    id: copyBanner
                    type: Kirigami.MessageType.Positive
                    text: qsTr("Reference copied to clipboard!")
                    visible: false
                    showCloseButton: true

                    function open() {
                        visible = true;
                        autoCloseTimer.restart();
                    }

                    Timer {
                        id: autoCloseTimer
                        interval: 3000
                        onTriggered: copyBanner.visible = false
                    }
                }
            }
        }
    }

    Kirigami.Dialog {
        id: confirmDialog
        title: qsTr("Confirm System Rebase")
        padding: Kirigami.Units.largeSpacing

        customFooterActions: [
            Kirigami.Action {
                text: qsTr("Perform Rebase")
                icon.name: "system-switch-user"
                onTriggered: {
                    var setObj = selectedOverlaySet
                    if (setObj) {
                        if (setObj.id === "__reset_all__") {
                            backend.queuePendingOverlayReset()
                        } else {
                            backend.queuePendingOverlaySet(setObj.layeredPackages || [], setObj.localPackages || [], setObj.removedPackages || [])
                        }
                    }
                    backend.rebaseSystem(page.fullRefSpec, {
                        prepPlasmaLogin: page.showPlasmaLoginPrep && page.prepPlasmaLogin
                    })
                    confirmDialog.close()
                }
            },
            Kirigami.Action {
                text: qsTr("Cancel")
                icon.name: "dialog-cancel"
                onTriggered: confirmDialog.close()
            }
        ]

        ColumnLayout {
            spacing: Kirigami.Units.mediumSpacing

            Controls.Label {
                text: qsTr("Are you sure you want to rebase your system to:")
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            Controls.TextField {
                text: page.fullRefSpec
                readOnly: true
                font.family: "monospace"
                Layout.fillWidth: true
                selectByMouse: true
            }

            Controls.Label {
                visible: selectedOverlaySet !== null
                text: selectedOverlaySet && selectedOverlaySet.id === "__reset_all__"
                      ? qsTr("All package overlays will be removed (start fresh).")
                      : qsTr("Applying Overlay Set: %1").arg(selectedOverlaySet ? selectedOverlaySet.name : "")
                font.bold: true
                color: selectedOverlaySet && selectedOverlaySet.id === "__reset_all__"
                       ? Kirigami.Theme.negativeTextColor
                       : Kirigami.Theme.highlightColor
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: Kirigami.Units.smallSpacing
                visible: page.showPlasmaLoginPrep

                Controls.Label {
                    text: qsTr("Desktop environment change")
                    font.bold: true
                    Layout.fillWidth: true
                }

                Controls.Label {
                    visible: page.prepPlasmaLogin
                    text: qsTr("You are switching to a Plasma base. Atomic Basejump will prepare the Plasma login manager account so the login screen works after reboot.")
                    wrapMode: Text.WordWrap
                    Layout.fillWidth: true
                }

                Controls.Label {
                    visible: !page.prepPlasmaLogin
                    text: qsTr("Warning: without preparing login accounts, the Plasma login screen may fail (black screen) if accounts were removed on a GNOME boot.")
                    wrapMode: Text.WordWrap
                    color: Kirigami.Theme.negativeTextColor
                    Layout.fillWidth: true
                }

                Controls.CheckBox {
                    checked: page.prepPlasmaLogin
                    text: qsTr("Prepare Plasma Login Manager accounts")
                    onToggled: page.prepPlasmaLogin = checked
                }
            }

            Controls.Label {
                text: qsTr("A new system deployment will be prepared and staged for reboot. Your user data and home directory will remain intact.")
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
                color: Kirigami.Theme.disabledTextColor
            }
        }
    }
}
