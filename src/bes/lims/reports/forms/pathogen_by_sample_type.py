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


from collections import OrderedDict

from bes.lims import messageFactory as _
from bes.lims.reports import get_matched_microorganisms_sample
from bes.lims.reports import get_potential_true_pathogen_microorganisms
from bes.lims.reports import count_by
from bes.lims.reports import get_received_samples
from bes.lims.reports.forms import CSVReport
from bika.lims import api
from senaite.ast.utils import get_identified_microorganisms


class PathogenBySampleType(CSVReport):
    """Pathogen by Sample type
    """

    def process_form(self):
        # get the samples that were received within the given year
        date_from = self.request.form.get("date_from")
        date_to = self.request.form.get("date_to")
        query = {
            "review_state": "published",
        }
        brains = get_received_samples(date_from, date_to, **query)
        samples = map(api.get_object, brains)

        # num of positive pathogen samples by month
        pathogen_microorganisms = get_potential_true_pathogen_microorganisms()
        positive_pathogen_samples = get_matched_microorganisms_sample(
            pathogen_microorganisms, samples
        )

        count_received = count_by(
            positive_pathogen_samples, "getSampleTypeTitle"
        )
        sample_types = count_received.keys()

        # Build the rows
        rows = []
        sample_groups = OrderedDict(
            [(sample_type, 0) for sample_type in sample_types]
        )
        pathogens_group_by_sample_type = {}

        for item in pathogen_microorganisms:
            pathogens_group_by_sample_type[item] = sample_groups.copy()

        for sample in positive_pathogen_samples:
            pathogens_in_sample = self.get_pathogen_sample(
                pathogen_microorganisms, sample
            )
            name = sample.getSampleTypeTitle()
            for pathogen in pathogens_in_sample:
                pathogens_group_by_sample_type[pathogen][name] += 1

        # Create a row for each pathogen
        for pathogen, sample_counts in pathogens_group_by_sample_type.items():
            row = [pathogen] + list(sample_counts.values()) + [sum(sample_counts.values())]  # noqa: E501
            rows.append(row)

        # Prepare the header
        headers = [_("Pathogens")] + sample_types + [_("Total")]
        rows.insert(0, headers)
        return rows

    def get_pathogen_sample(self, pathogen_microorganisms, sample):
        """Returns the number of pathogen in sample
        """
        # Get the names of the selected microorganisms
        microorganisms = get_identified_microorganisms(sample)
        microorganisms = [api.get_title(m) for m in microorganisms]

        pathogens = [
            item for item in microorganisms if item in pathogen_microorganisms
        ]
        return pathogens
