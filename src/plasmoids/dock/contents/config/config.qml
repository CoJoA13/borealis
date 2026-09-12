import QtQuick
import org.kde.plasma.configuration

ConfigModel {
    ConfigCategory {
        name: i18nd("plasma_applet_org.borealis.dock", "General")
        icon: "preferences-desktop-icons"
        source: "configGeneral.qml"
    }
}
