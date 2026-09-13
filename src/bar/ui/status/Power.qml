/*
    Power modes and Stay Awake, from Plasma's power management module.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.plasma.private.batterymonitor as Batterymonitor

QtObject {
    id: power

    // silent: the Control Center shows changes itself, and changes made
    // elsewhere shouldn't pop up an on-screen display from the bar
    property var profilesControl: Batterymonitor.PowerProfilesControl {
        isSilent: true
    }
    property var inhibitionControl: Batterymonitor.InhibitionControl {
        isSilent: true
    }

    readonly property var profiles: profilesControl.profiles || []
    readonly property bool profilesAvailable: !!profilesControl.isPowerProfileDaemonInstalled && profiles.length > 0
    readonly property string profile: profilesControl.activeProfile || ""
    // why Performance can't be picked right now, or why it runs slower
    readonly property string performanceBlocked: profilesControl.inhibitionReason || ""
    readonly property string performanceDegraded: profilesControl.degradationReason || ""
    // apps holding on to a mode: [{Name, Icon, Profile, Reason}]
    readonly property var holds: Array.isArray(profilesControl.profileHolds) ? profilesControl.profileHolds : []

    readonly property bool awake: !!inhibitionControl.isManuallyInhibited

    function setProfile(name) {
        if (name !== profile && profiles.indexOf(name) >= 0) {
            profilesControl.setProfile(name);
        }
    }
    function setAwake(on) {
        if (on) {
            inhibitionControl.inhibit(qsTr("Stay Awake is on in the Control Center"));
        } else {
            inhibitionControl.uninhibit();
        }
    }
}
