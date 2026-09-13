/*
    A quiet line of explanation under a setting.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

QQC2.Label {
    Layout.fillWidth: true
    // a wrapped label otherwise asks for its whole unwrapped line as its
    // minimum, and a narrow form's single column can't get narrower than that
    Layout.minimumWidth: Kirigami.Units.gridUnit * 8
    Layout.preferredWidth: Kirigami.Units.gridUnit * 26
    Layout.maximumWidth: Kirigami.Units.gridUnit * 26
    wrapMode: Text.WordWrap
    opacity: 0.7
    font: Kirigami.Theme.smallFont
}
