/*
    A small drawing of the desktop a preset, or a theme choice, makes: the
    wallpaper, the bar, a window with its title bar buttons, and the dock.
    `summary` is what desktoppresets.thumb() gives.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami

Item {
    id: thumb

    property var summary: ({})

    readonly property string variant: summary.variant || "dark"
    readonly property bool dark: variant !== "light"
    readonly property color accent: summary.accent || "#8b9cff"
    // the drawing is 160 units wide and 100 high
    readonly property real u: height / 100
    readonly property real barOpacity: summary.barOpacity === undefined ? 0.72 : summary.barOpacity
    // near enough to Borealis Dark and Light
    readonly property color ink: dark ? "#e6e9f2" : "#1b2130"
    readonly property color paper: dark ? "#171d2c" : "#fbfcfe"
    readonly property color titleBar: dark ? "#20283a" : "#e8ecf4"
    readonly property color glass: dark ? "#141a29" : "#fafbfe"

    implicitWidth: Kirigami.Units.gridUnit * 10
    implicitHeight: Math.round(implicitWidth * 0.625)

    // the wallpaper; day and night shows both
    Rectangle {
        anchors.fill: parent
        radius: thumb.u * 6
        gradient: Gradient {
            GradientStop { position: 0; color: thumb.variant === "dark" ? "#1c2645" : "#f6f8fc" }
            GradientStop { position: 1; color: thumb.variant === "dark" ? "#0e121b" : "#d9e0ef" }
        }
    }
    Item {
        visible: thumb.variant === "auto"
        width: parent.width / 2
        height: parent.height
        clip: true
        Rectangle {
            width: thumb.width
            height: thumb.height
            radius: thumb.u * 6
            gradient: Gradient {
                GradientStop { position: 0; color: "#1c2645" }
                GradientStop { position: 1; color: "#0e121b" }
            }
        }
    }
    // an aurora across the sky
    Rectangle {
        x: thumb.u * 20
        y: thumb.u * 30
        width: thumb.u * 130
        height: thumb.u * 18
        radius: height / 2
        rotation: -14
        opacity: thumb.dark ? 0.4 : 0.25
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "transparent" }
            GradientStop { position: 0.35; color: thumb.accent }
            GradientStop { position: 0.7; color: "#5fe0c8" }
            GradientStop { position: 1; color: "transparent" }
        }
    }

    // a window
    Rectangle {
        id: window
        readonly property string dockEdge: thumb.summary.dockPosition || "bottom"
        x: thumb.width * 0.2 + (dockEdge === "left" ? thumb.u * 10 : dockEdge === "right" ? -thumb.u * 10 : 0)
        y: thumb.u * 17
        width: thumb.width * 0.6
        height: thumb.u * 52
        radius: thumb.u * 2.5
        color: thumb.paper
        border.width: 1
        border.color: Qt.rgba(thumb.ink.r, thumb.ink.g, thumb.ink.b, 0.14)

        Rectangle {
            x: 1
            y: 1
            width: parent.width - 2
            height: thumb.u * 8
            radius: window.radius
            color: thumb.titleBar
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: parent.height / 2
                color: parent.color
            }
        }
        Row {
            id: buttons
            readonly property bool atLeft: thumb.summary.buttonsLeft === true
            readonly property var shown: thumb.summary.buttons || ["minimize", "maximize", "close"]
            x: atLeft ? thumb.u * 3 : parent.width - width - thumb.u * 3
            y: thumb.u * 4 + 1 - height / 2
            spacing: thumb.u * 1.4
            Repeater {
                // at the left, close comes first
                model: (buttons.atLeft ? ["close", "minimize", "maximize"] : ["minimize", "maximize", "close"])
                    .filter(name => buttons.shown.indexOf(name) >= 0)
                delegate: Rectangle {
                    required property string modelData
                    width: thumb.u * 4.4
                    height: thumb.u * 2.4
                    radius: height / 2
                    color: modelData === "close" ? "#ff6b81" : modelData === "minimize" ? "#5fe0c8" : thumb.accent
                }
            }
        }
        Column {
            x: thumb.u * 5
            y: thumb.u * 15
            spacing: thumb.u * 3.4
            Repeater {
                model: [0.7, 0.48, 0.6, 0.34]
                delegate: Rectangle {
                    required property real modelData
                    width: window.width * modelData
                    height: thumb.u * 2.6
                    radius: height / 2
                    color: Qt.rgba(thumb.ink.r, thumb.ink.g, thumb.ink.b, 0.16)
                }
            }
        }
    }

    // the bar: floating, or flush along the top
    Item {
        id: bar
        readonly property bool floating: thumb.summary.barFloating !== false
        readonly property string clock: thumb.summary.clock === undefined ? "center" : thumb.summary.clock
        x: floating ? thumb.u * 4 : 0
        y: floating ? thumb.u * 3.5 : 0
        width: thumb.width - 2 * x
        height: thumb.u * 7.5

        Item {
            anchors.fill: parent
            opacity: 0.3 + 0.65 * thumb.barOpacity
            Rectangle {
                anchors.fill: parent
                radius: bar.floating ? height / 2 : thumb.u * 6
                color: thumb.glass
            }
            Rectangle {
                visible: !bar.floating
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: parent.height / 2
                color: thumb.glass
            }
        }
        // the Borealis menu
        Rectangle {
            x: bar.height * 0.5
            anchors.verticalCenter: parent.verticalCenter
            width: bar.height * 0.42
            height: width
            radius: width / 2
            color: thumb.accent
        }
        Rectangle {
            id: clockMark
            visible: bar.clock !== ""
            width: thumb.u * 13
            height: bar.height * 0.3
            radius: height / 2
            anchors.verticalCenter: parent.verticalCenter
            x: bar.clock === "left" ? bar.height * 1.4
                : bar.clock === "right" ? bar.width - width - bar.height * 0.6 : (bar.width - width) / 2
            color: Qt.rgba(thumb.ink.r, thumb.ink.g, thumb.ink.b, 0.75)
        }
        // the Control Center's glyphs
        Row {
            spacing: bar.height * 0.2
            anchors.verticalCenter: parent.verticalCenter
            x: bar.width - width - bar.height * 0.6 - (bar.clock === "right" ? clockMark.width + bar.height * 0.4 : 0)
            Repeater {
                model: 3
                delegate: Rectangle {
                    width: bar.height * 0.3
                    height: width
                    radius: width / 2
                    color: Qt.rgba(thumb.ink.r, thumb.ink.g, thumb.ink.b, 0.5)
                }
            }
        }
    }

    // the dock, faint when it hides until needed
    Item {
        id: dock
        readonly property string edge: thumb.summary.dockPosition || "bottom"
        readonly property bool upright: edge !== "bottom"
        readonly property real icon: Math.max(4, Math.min(13, (thumb.summary.dockSize || 48) / 48 * 7)) * thumb.u
        readonly property real gap: icon * 0.22
        readonly property real zoom: Math.max(1, Math.min(3, thumb.summary.dockZoom || 1))
        readonly property var colors: [thumb.accent, "#5fe0c8", "#ffc46b", "#ff6b81", "#b18cff", "#6fb6ff"]
        readonly property real length: colors.length * icon + (colors.length + 1) * gap

        opacity: thumb.summary.dockHidden ? 0.3 : 1
        width: upright ? icon + 2 * gap : length
        height: upright ? length : icon + 2 * gap
        x: edge === "left" ? thumb.u * 3 : edge === "right" ? thumb.width - width - thumb.u * 3 : (thumb.width - width) / 2
        y: upright ? (thumb.height - height) / 2 + thumb.u * 4 : thumb.height - height - thumb.u * 3

        Rectangle {
            anchors.fill: parent
            radius: dock.icon * 0.4
            color: Qt.rgba(thumb.glass.r, thumb.glass.g, thumb.glass.b, 0.75)
            border.width: 1
            border.color: Qt.rgba(thumb.ink.r, thumb.ink.g, thumb.ink.b, 0.12)
        }
        Grid {
            anchors.centerIn: parent
            columns: dock.upright ? 1 : dock.colors.length
            spacing: dock.gap
            Repeater {
                model: dock.colors
                delegate: Rectangle {
                    required property color modelData
                    required property int index
                    width: dock.icon
                    height: dock.icon
                    radius: width * 0.28
                    // the third icon is under the pointer
                    scale: dock.upright ? 1 : index === 2 ? 1 + (dock.zoom - 1) * 0.55
                        : index === 1 || index === 3 ? 1 + (dock.zoom - 1) * 0.2 : 1
                    transformOrigin: Item.Bottom
                    gradient: Gradient {
                        GradientStop { position: 0; color: Qt.lighter(modelData, 1.2) }
                        GradientStop { position: 1; color: modelData }
                    }
                }
            }
        }
    }
}
