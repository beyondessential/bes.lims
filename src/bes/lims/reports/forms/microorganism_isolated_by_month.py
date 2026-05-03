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


from bes.lims import messageFactory as _
from bes.lims.config import MONTHS
from bes.lims.reports import get_received_samples_by_year
from bes.lims.reports.forms import CSVReport
from bika.lims import api
from collections import OrderedDict
from senaite.ast.utils import get_identified_microorganisms


class MicroorganismIsolatedByMonth(CSVReport):
    """The number of Microorganism Isolated each month
    """

    def process_form(self):
        year = int(self.request.form.get("year"))
        brains = get_received_samples_by_year(year, review_state="published")
        samples = map(api.get_object, brains)

        # Build the rows
        rows = []

        # Prepare the header
        months = [MONTHS[num] for num in range(1, 13)]
        headers = [_("Microorganism")] + months + [_("Total")]
        rows.append(headers)

        # initialize the organism-month map
        groups = {}

        for sample in samples:

            # get the identified organisms for this samples
            organisms = get_identified_microorganisms(sample)

            # get the month when the sample was received
            month = int(sample.getDateReceived().month())

            # fill the organism-month mapping
            for organism in organisms:

                # get the title of the organism
                title = organism.title

                months = groups.get(organism)
                if not months:
                    groups[title] = OrderedDict.fromkeys(range(1, 13), 0)
                groups[title][month] += 1

        # Create a row for each microorganism
        for organism, counts in groups.items():
            row = [organism] + list(counts.values()) + [sum(counts.values())]
            rows.append(row)

        return rows
