import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root
    title: qsTr("Atomic Basejump - System Image Manager")
    width: 960
    height: 680
    minimumWidth: 840
    minimumHeight: 560

    globalDrawer: Kirigami.GlobalDrawer {
        title: qsTr("Atomic Basejump")
        titleIcon: "io.github.joshuaroman.AtomicBasejump"
        collapsible: false
        modal: false
        width: Kirigami.Units.gridUnit * 12

        contentItem: ColumnLayout {
            spacing: 0
            
            Controls.ItemDelegate {
                text: qsTr("Deployments")
                icon.name: "drive-harddisk"
                Layout.fillWidth: true
                highlighted: pageStack.currentItem === overviewPage
                onClicked: pageStack.replace(overviewPage)
            }
            Controls.ItemDelegate {
                text: qsTr("Image Browser")
                icon.name: "system-search"
                Layout.fillWidth: true
                highlighted: pageStack.currentItem === imageBrowserPage
                onClicked: pageStack.replace(imageBrowserPage)
            }
            Controls.ItemDelegate {
                text: qsTr("Overlay Sets")
                icon.name: "layers"
                Layout.fillWidth: true
                highlighted: pageStack.currentItem === overlaySetsPage
                onClicked: pageStack.replace(overlaySetsPage)
            }
            Controls.ItemDelegate {
                text: qsTr("Settings")
                icon.name: "configure"
                Layout.fillWidth: true
                highlighted: pageStack.currentItem && pageStack.currentItem.objectName === "settingsPage"
                onClicked: pageStack.replace(settingsPageComponent)
            }
            Controls.ItemDelegate {
                text: qsTr("About")
                icon.name: "help-about"
                Layout.fillWidth: true
                highlighted: pageStack.currentItem === aboutPage
                onClicked: pageStack.replace(aboutPage)
            }
            
            Item { Layout.fillHeight: true } // spacer
        }
    }

    pageStack.initialPage: overviewPage

    OverviewPage {
        id: overviewPage
        objectName: "overviewPage"
        width: pageStack.width
        visible: false
    }

    ImageBrowserPage {
        id: imageBrowserPage
        objectName: "imageBrowserPage"
        width: pageStack.width
        visible: false
    }

    OverlaySetsPage {
        id: overlaySetsPage
        objectName: "overlaySetsPage"
        width: pageStack.width
        visible: false
    }

    Component {
        id: settingsPageComponent

        SettingsPage {
            objectName: "settingsPage"
        }
    }

    AboutPage {
        id: aboutPage
        objectName: "aboutPage"
        width: pageStack.width
        visible: false
    }

    LogDialog {
        id: globalLogDialog
    }
}
