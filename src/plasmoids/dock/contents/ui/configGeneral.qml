import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.FormLayout {
    id: page
    property alias cfg_iconSize: iconSize.value
    property alias cfg_magnification: zoom.value
    property alias cfg_reach: reach.value
    property alias cfg_onlyCurrentDesktop: currentDesktop.checked
    property alias cfg_showTrash: showTrash.checked

    RowLayout {
        Kirigami.FormData.label: i18nd("plasma_applet_org.borealis.dock", "Icon size:")
        QQC2.Slider {
            id: iconSize
            from: 24
            to: 96
            stepSize: 2
            Layout.preferredWidth: Kirigami.Units.gridUnit * 12
        }
        QQC2.Label { text: Math.round(iconSize.value) + " px" }
    }

    RowLayout {
        Kirigami.FormData.label: i18nd("plasma_applet_org.borealis.dock", "Magnification:")
        QQC2.Slider {
            id: zoom
            from: 100
            to: 220
            stepSize: 5
            Layout.preferredWidth: Kirigami.Units.gridUnit * 12
        }
        QQC2.Label {
            text: zoom.value <= 100 ? i18nd("plasma_applet_org.borealis.dock", "off")
                                    : Math.round(zoom.value) + " %"
        }
    }

    RowLayout {
        Kirigami.FormData.label: i18nd("plasma_applet_org.borealis.dock", "Spread:")
        QQC2.Slider {
            id: reach
            from: 1
            to: 6
            stepSize: 1
            Layout.preferredWidth: Kirigami.Units.gridUnit * 12
        }
        QQC2.Label {
            text: i18ndp("plasma_applet_org.borealis.dock", "%1 icon either side", "%1 icons either side",
                         Math.round(reach.value))
        }
    }

    QQC2.CheckBox {
        id: currentDesktop
        Kirigami.FormData.label: i18nd("plasma_applet_org.borealis.dock", "Windows:")
        text: i18nd("plasma_applet_org.borealis.dock", "Only from the current desktop")
    }

    QQC2.CheckBox {
        id: showTrash
        text: i18nd("plasma_applet_org.borealis.dock", "Show the trash at the end")
    }

    QQC2.Label {
        Layout.maximumWidth: Kirigami.Units.gridUnit * 20
        wrapMode: Text.WordWrap
        opacity: 0.7
        font: Kirigami.Theme.smallFont
        text: i18nd("plasma_applet_org.borealis.dock",
                    "Drop an application on the dock to pin it, or use the right-click menu. The panel's own height limits how far icons can grow.")
    }
}
