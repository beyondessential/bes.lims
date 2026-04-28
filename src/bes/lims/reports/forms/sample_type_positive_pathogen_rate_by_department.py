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
from bes.lims import messageFactory as _
from bes.lims.reports import calculate_rate
from bes.lims.reports import count_by
from bes.lims.reports import get_potential_true_pathogen_microorganisms
from bes.lims.reports import get_matched_microorganisms_sample
from bes.lims.reports import get_received_samples
from bes.lims.reports import group_by

from bes.lims.reports.forms import CSVReport


class SampleTypePositivePathogenRateByDepartment(CSVReport):
    """True positive pathogen rate by department for each sample type
    """

    def process_form(self):
        date_from = self.request.form.get("date_from")
        date_to = self.request.form.get("date_to")
        query = {
            "review_state": "published",
        }
        brains = get_received_samples(date_from, date_to, **query)
        samples = list(map(api.get_object, brains))
        samples_by_sample_type = group_by(samples, "getSampleTypeTitle")
        departments = sorted(
            set(map(lambda sample: sample.getWardDepartment(), samples)),
            key=lambda dept: str(dept)
        )

        microorganisms = get_potential_true_pathogen_microorganisms()
        rows = []
        for sample_type, samples_in_sample_type in samples_by_sample_type.items():  # noqa: E501
            counted_samples = count_by(samples_in_sample_type, "getWardDepartment")  # noqa: E501
            matched_samples = get_matched_microorganisms_sample(
                microorganisms, samples_in_sample_type
            )
            counted_pathogens = count_by(matched_samples, "getWardDepartment")

            row_1 = [_(
                "Total of number of {} samples with growth of potential pathogens"  # noqa: E501
            ).format(sample_type)]
            row_2 = [_("Total number {} samples tested").format(sample_type)]
            row_3 = [_("True positive rate (%) - {}").format(sample_type)]

            for dept in departments:
                total_samples = counted_samples.get(dept, 0)
                total_pathogens = counted_pathogens.get(dept, 0)
                row_1.append(total_pathogens)
                row_2.append(total_samples)
                row_3.append(calculate_rate(total_samples, total_pathogens))

            rows.extend([row_1, row_2, row_3])

        department_titles = list(
            map(lambda dept: dept.Title() if dept else "Unknown", departments)
        )
        headers = ["Departments"] + department_titles
        rows.insert(0, headers)

        return rows
