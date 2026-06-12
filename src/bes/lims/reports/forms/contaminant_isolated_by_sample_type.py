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
from bes.lims.reports import get_contaminant_microorganisms
from bes.lims.reports import get_matched_microorganisms_sample
from bes.lims.reports import get_received_samples
from bes.lims.reports import count_by
from bes.lims.reports.forms import CSVReport
from bika.lims import api
from collections import OrderedDict
from senaite.ast.utils import get_identified_microorganisms


class ContaminantBySampleType(CSVReport):
    """Contaminant by Sample type
    """

    def process_form(self):
        date_from = self.request.form.get("date_from")
        date_to = self.request.form.get("date_to")
        query = {
            "review_state": "published",
        }
        brains = get_received_samples(date_from, date_to, **query)
        samples = map(api.get_object, brains)

        # num of positive contaminants samples by month
        contaminant_microorganisms = get_contaminant_microorganisms()
        probable_contaminant_samples = get_matched_microorganisms_sample(
            contaminant_microorganisms, samples
        )

        count_received = count_by(
            probable_contaminant_samples, "getSampleTypeTitle"
        )
        sample_types = count_received.keys()

        # Build the rows
        rows = []
        sample_groups = OrderedDict(
            [(sample_type, 0) for sample_type in sample_types]
        )
        contaminants_group_by_sample_type = {}

        for item in contaminant_microorganisms:
            contaminants_group_by_sample_type[item] = sample_groups.copy()

        for sample in probable_contaminant_samples:
            contaminants_in_sample = self.get_contaminant_sample(
                contaminant_microorganisms, sample
            )
            sample_type = sample.getSampleType()
            name = api.get_title(sample_type)
            for contaminants in contaminants_in_sample:
                contaminants_group_by_sample_type[contaminants][name] += 1

        # Create a row for each pathogen
        for contaminant, sample_counts in contaminants_group_by_sample_type.items():  # noqa: E501
            row = [contaminant] + list(sample_counts.values()) + [sum(sample_counts.values())]  # noqa: E501
            rows.append(row)

        # Prepare the header
        headers = [_("Probable Contaminants")] + sample_types + [_("Total")]
        rows.insert(0, headers)
        return rows

    def get_contaminant_sample(self, contaminant_microorganisms, sample):
        """Returns the number of pathogen in sample
        """
        # Get the names of the selected microorganisms
        microorganisms = get_identified_microorganisms(sample)
        microorganisms = [api.get_title(m) for m in microorganisms]

        contaminant = [
            item for item in microorganisms
            if item in contaminant_microorganisms
        ]
        return contaminant
