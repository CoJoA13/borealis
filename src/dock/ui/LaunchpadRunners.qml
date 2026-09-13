/*
    Plasma's runners for Launchpad's search: System Settings pages, sums,
    unit conversions, files. Loaded on its own, so the rest of Launchpad still
    works if this private Plasma module ever changes or goes away.
    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.plasma.private.kicker as Kicker

Kicker.RunnerModel {
    id: model

    property var results: []

    // apps are Launchpad's own grid; these add what it can't find
    runners: ["krunner_systemsettings", "calculator", "unitconverter", "baloosearch", "krunner_recentdocuments"]
    mergeResults: false

    function collect() {
        const out = [];
        for (let g = 0; g < count && out.length < 5; g++) {
            const matches = modelForRow(g);
            const group = String(data(index(g, 0), Qt.DisplayRole) || "");
            for (let i = 0; matches && i < matches.count && out.length < 5; i++) {
                const idx = matches.index(i, 0);
                out.push({
                    group: g,
                    row: i,
                    groupName: group,
                    text: String(matches.data(idx, Qt.DisplayRole) || ""),
                    subtext: String(matches.data(idx, Qt.UserRole + 1) || ""),
                    icon: matches.data(idx, Qt.DecorationRole) || ""
                });
            }
        }
        results = out;
    }

    function run(result) {
        const matches = modelForRow(result.group);
        if (matches) {
            matches.trigger(result.row, "", null);
        }
    }

    onQueryFinished: collect()
    onCountChanged: collect()
}
