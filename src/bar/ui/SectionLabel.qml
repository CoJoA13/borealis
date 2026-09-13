/*
    A small heading between groups of rows on a Control Center page.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Text {
    Layout.fillWidth: true
    Layout.topMargin: 6
    Layout.leftMargin: 10
    textFormat: Text.PlainText
    elide: Text.ElideRight
    font.pointSize: Kirigami.Theme.smallFont.pointSize
    font.weight: Font.DemiBold
    color: Kirigami.Theme.disabledTextColor
}
