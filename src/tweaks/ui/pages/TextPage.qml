/*
    Borealis Tweaks, the Text & Pointer page: the fonts, how text is drawn,
    the pointer, and icon sizes in apps.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "../controls"

Kirigami.ScrollablePage {
    id: page
    title: qsTr("Text & Pointer")

    readonly property var v: textSettings.values

    component TextToggle: Toggle {
        target: textSettings
    }
    component TextChoice: Choice {
        target: textSettings
    }

    // one font: its family and its size
    component FontRow: RowLayout {
        id: row
        required property string key
        property bool fixedOnly: false
        readonly property var current: page.v[key] || ({family: "", size: 10})
        readonly property var families: fixedOnly ? textSettings.fixedFamilies : textSettings.families
        spacing: Kirigami.Units.smallSpacing

        QQC2.ComboBox {
            Layout.fillWidth: true
            Layout.minimumWidth: Kirigami.Units.gridUnit * 7
            Layout.maximumWidth: Kirigami.Units.gridUnit * 14
            model: row.families
            currentIndex: row.families.indexOf(row.current.family)
            displayText: row.current.family
            onActivated: index => {
                textSettings.set(row.key, {family: row.families[index], size: row.current.size});
                currentIndex = Qt.binding(() => row.families.indexOf(row.current.family));
            }
        }
        QQC2.SpinBox {
            from: 6
            to: 36
            value: Math.round(row.current.size)
            onValueModified: textSettings.set(row.key, {family: row.current.family, size: value})
        }
        QQC2.Label {
            text: qsTr("pt")
            opacity: 0.7
        }
    }

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Fonts")
            }
            FontRow {
                Kirigami.FormData.label: qsTr("Everywhere:")
                key: "font"
            }
            FontRow {
                Kirigami.FormData.label: qsTr("Fixed width:")
                key: "fixed"
                fixedOnly: true
            }
            FontRow {
                Kirigami.FormData.label: qsTr("Small print:")
                key: "smallestReadableFont"
            }
            FontRow {
                Kirigami.FormData.label: qsTr("Toolbars:")
                key: "toolBarFont"
            }
            FontRow {
                Kirigami.FormData.label: qsTr("Menus:")
                key: "menuFont"
            }
            FontRow {
                Kirigami.FormData.label: qsTr("Window titles:")
                key: "activeFont"
            }
            Hint {
                text: qsTr("Borealis uses Inter, with JetBrains Mono for fixed width. Apps change font at once; window titles may keep theirs until you next log in.")
            }
            QQC2.Button {
                text: qsTr("Reset fonts")
                icon.name: "edit-undo"
                onClicked: textSettings.resetFonts()
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("How text is drawn")
            }
            TextToggle {
                Kirigami.FormData.label: qsTr("Smooth edges:")
                key: "antialias"
            }
            TextChoice {
                Kirigami.FormData.label: qsTr("Hinting:")
                enabled: page.v.antialias === true
                key: "hinting"
                choices: [["none", qsTr("None")], ["slight", qsTr("Slight")], ["medium", qsTr("Medium")],
                          ["full", qsTr("Full")]]
            }
            TextChoice {
                Kirigami.FormData.label: qsTr("Sub-pixel colour:")
                enabled: page.v.antialias === true
                key: "subpixel"
                choices: [["none", qsTr("Off")], ["rgb", qsTr("RGB")], ["bgr", qsTr("BGR")],
                          ["vrgb", qsTr("Vertical RGB")], ["vbgr", qsTr("Vertical BGR")]]
            }
            Hint {
                text: qsTr("Apps you open from now on draw their text this way.")
            }
            QQC2.Button {
                text: qsTr("Reset text drawing")
                icon.name: "edit-undo"
                onClicked: textSettings.resetRendering()
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Pointer")
            }
            TextChoice {
                Kirigami.FormData.label: qsTr("Pointer:")
                key: "cursorTheme"
                choices: textSettings.cursorThemes.map(theme => [theme.id, theme.name])
            }
            TextChoice {
                Kirigami.FormData.label: qsTr("Size:")
                key: "cursorSize"
                choices: textSettings.cursorSizes.map(size => [size, qsTr("%1 px").arg(size)])
            }
            QQC2.Button {
                text: qsTr("Reset the pointer")
                icon.name: "edit-undo"
                onClicked: textSettings.resetPointer()
            }

            Kirigami.Separator {
                Kirigami.FormData.isSection: true
                Kirigami.FormData.label: qsTr("Icons in apps")
            }
            TextChoice {
                Kirigami.FormData.label: qsTr("Toolbars:")
                key: "toolbarIcons"
                choices: [16, 22, 32, 48].map(size => [size, qsTr("%1 px").arg(size)])
            }
            TextChoice {
                Kirigami.FormData.label: qsTr("Main toolbar:")
                key: "mainToolbarIcons"
                choices: [16, 22, 32, 48].map(size => [size, qsTr("%1 px").arg(size)])
            }
            TextChoice {
                Kirigami.FormData.label: qsTr("Lists and sidebars:")
                key: "smallIcons"
                choices: [16, 22, 32].map(size => [size, qsTr("%1 px").arg(size)])
            }
            TextChoice {
                Kirigami.FormData.label: qsTr("Dialogs:")
                key: "dialogIcons"
                choices: [32, 48, 64].map(size => [size, qsTr("%1 px").arg(size)])
            }
            Hint {
                text: qsTr("KDE apps such as Dolphin and Kate follow these; Plasma, the dock and the bar keep their own sizes.")
            }
            QQC2.Button {
                text: qsTr("Reset icon sizes")
                icon.name: "edit-undo"
                onClicked: textSettings.resetIcons()
            }
        }
    }
}
