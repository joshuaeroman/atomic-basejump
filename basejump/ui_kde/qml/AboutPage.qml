import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    title: qsTr("About Atomic Basejump")
    footer: StatusBar {}

    ColumnLayout {
        anchors.centerIn: parent
        spacing: Kirigami.Units.largeSpacing

        Kirigami.Icon {
            source: "io.github.joshuaroman.AtomicBasejump"
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: Kirigami.Units.iconSizes.huge
            Layout.preferredHeight: Kirigami.Units.iconSizes.huge
        }

        Kirigami.Heading {
            text: appInfo.displayName
            level: 1
            Layout.alignment: Qt.AlignHCenter
        }

        Controls.Label {
            text: qsTr("An rpm-ostree deployment manager for Fedora Atomic")
            Layout.alignment: Qt.AlignHCenter
        }

        Controls.Label {
            text: qsTr("Version: %1").arg(appInfo.version)
            opacity: 0.7
            Layout.alignment: Qt.AlignHCenter
        }

        Controls.Label {
            text: qsTr("Build Time: %1").arg(appInfo.buildTimestamp)
            opacity: 0.7
            Layout.alignment: Qt.AlignHCenter
        }

        Controls.Label {
            text: qsTr("License: %1").arg(appInfo.license)
            opacity: 0.7
            Layout.alignment: Qt.AlignHCenter
        }

        Controls.Label {
            text: appInfo.homepage
            opacity: 0.7
            Layout.alignment: Qt.AlignHCenter
        }
    }
}
