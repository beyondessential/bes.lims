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
from bes.lims.reports import get_contaminant_microorganisms
from bes.lims.reports import get_matched_microorganisms_sample
from bes.lims.reports import get_received_samples_by_year
from bes.lims.reports.forms import CSVReport
from bika.lims import api
from collections import OrderedDict
from senaite.ast.utils import get_identified_microorganisms


class ContaminantIsolatedRateByMonth(CSVReport):
    """Probable Contaminant Isolated by month
    """

    def process_form(self):
        year = int(self.request.form.get("year"))
        brains = get_received_samples_by_year(year, review_state="published")

        samples = map(api.get_object, brains)

        # num of positive contaminants samples by month
        contaminant_microorganisms = get_contaminant_microorganisms()
        probable_contaminant_samples = get_matched_microorganisms_sample(
            contaminant_microorganisms, samples
        )

        # Build the rows
        rows = []

        month_groups = OrderedDict([(month, 0) for month in range(1, 13)])
        contaminants_group_by_month = {}

        for item in contaminant_microorganisms:
            contaminants_group_by_month[item] = month_groups.copy()

        for sample in probable_contaminant_samples:
            contaminants_in_sample = self.get_contaminant_sample(
                contaminant_microorganisms, sample
            )
            received = sample.getDateReceived()
            month = received.month()
            for contaminant in contaminants_in_sample:
                contaminants_group_by_month[contaminant][month] += 1

        # Create a row for each contaminant
        for contaminant, month_counts in contaminants_group_by_month.items():
            row = [contaminant] + list(month_counts.values()) + [sum(month_counts.values())]  # noqa: E501
            rows.append(row)

        # Prepare the header
        months = [MONTHS[num] for num in range(1, 13)]
        headers = [_("Contaminants")] + months + [_("Total")]
        rows.insert(0, headers)
        return rows

    def get_contaminant_sample(self, contaminant_microorganisms, sample):
        """Returns a List of contaminants in sample
        """
        # Get the names of the selected microorganisms
        microorganisms = get_identified_microorganisms(sample)
        microorganisms = [api.get_title(m) for m in microorganisms]

        contaminants = [
            item for item in microorganisms
            if item in contaminant_microorganisms
        ]
        return contaminants
