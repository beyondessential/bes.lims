# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# BES.LIMS is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright 2024-2025 by it's authors.
# Some rights reserved, see README and LICENSE.


from bika.lims import api
from collections import OrderedDict
from plone.memoize import view
from bes.lims import messageFactory as _
from bes.lims.config import MONTHS
from bes.lims.reports import get_received_samples_by_year
from bes.lims.reports.forms import CSVReport


class ASTPanelByMonth(CSVReport):
    """AST panel used each month
    """

    def process_form(self):
        year = int(self.request.form.get("year"))
        brains = get_received_samples_by_year(year, review_state="published")
        samples = map(api.get_object, brains)

        # Build the rows
        rows = []
        groups = {}

        for sample in samples:
            panels = self.get_sample_panel_titles(sample)
            month = sample.getDateReceived().month()

            # fill the panels-months mapping
            for panel in panels:
                panel_by_months = groups.get(panel)
                if not panel_by_months:
                    groups[panel] = OrderedDict.fromkeys(range(1, 13), 0)

                groups[panel][month] += 1

        # Sort the panels alphabetically
        panel_groups = sorted(groups.keys())

        # Add row for each panel
        for panel in panel_groups:
            month_counts = groups[panel].values()
            row = [panel] + month_counts + [sum(month_counts)]
            rows.append(row)

        # Prepare the header
        months = [MONTHS[num] for num in range(1, 13)]
        headers = [_("AST Panel")] + months + [_("Total")]
        rows.insert(0, headers)
        return rows

    @view.memoize
    def get_panel_title(self, uid):
        """Returns the title of the panel based on the given uid
        """
        obj = api.get_object_by_uid(uid)
        return api.get_title(obj)

    def get_sample_panel_titles(self, sample):
        """Returns the list panel title of sample
        """
        sample.panels = getattr(sample, "panels", []) or []
        panels = map(self.get_panel_title, sample.panels)
        return panels
