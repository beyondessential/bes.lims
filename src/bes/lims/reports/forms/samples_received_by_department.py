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
from bes.lims.reports import count_by
from bes.lims.reports import get_received_samples
from bes.lims.reports import group_by
from bes.lims.reports.forms import CSVReport


class SamplesReceivedByDepartment(CSVReport):
    """Samples received by department
    """

    def process_form(self):
        # get the published samples within the period
        dt_from = self.request.form.get("date_from")
        dt_to = self.request.form.get("date_to")
        brains = get_received_samples(dt_from, dt_to, review_state="published")

        # Get the titles of the sample types
        sample_types = map(lambda brain: brain.getSampleTypeTitle, brains)
        sample_types = sorted(list(set(sample_types)))

        # add the first row (header)
        rows = [[_("Department")] + sample_types]

        # group the samples by (Ward) department
        samples_by_dept = group_by(brains, "getWardDepartment")

        for dept, samples_in_dept in samples_by_dept.items():

            # group and count the samples from this department by type
            counts = count_by(samples_in_dept, "getSampleTypeTitle")

            # get the samples count for each registered sample type
            sample_counts = map(lambda st: counts.get(st, 0), sample_types)

            # build the row
            rows.append([dept] + sample_counts)

        return rows
