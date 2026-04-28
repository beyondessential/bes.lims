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
from bes.lims.config import MONTHS
from bes.lims.reports import calculate_rate
from bes.lims.reports import count_by
from bes.lims.reports import get_contaminant_microorganisms
from bes.lims.reports import get_matched_microorganisms_sample
from bes.lims.reports import get_received_samples_by_year
from bes.lims.reports import get_target_patient_samples
from bes.lims.reports import group_by
from bes.lims.reports.forms import CSVReport


class SampleTypeContaminationRateByMonth(CSVReport):
    """Contamination rate by month for each sample type
    """

    def process_form(self):
        year = int(self.request.form.get("year"))
        brains = get_received_samples_by_year(year, review_state="published")
        samples = list(map(api.get_object, brains))
        target_patient = self.request.form.get("target_patient")
        samples = list(get_target_patient_samples(target_patient, samples))
        samples_by_sample_type = group_by(samples, "getSampleTypeTitle")

        microorganisms = get_contaminant_microorganisms()

        rows = []
        for sample_type, samples_in_sample_type in samples_by_sample_type.items():  # noqa: E501
            counted_samples = count_by(samples_in_sample_type, "getDateReceived")  # noqa: E501
            matched_samples = get_matched_microorganisms_sample(
                microorganisms, samples_in_sample_type
            )
            count_contamination = count_by(matched_samples, "getDateReceived")

            row_1 = [_(
                "Total of number of {} samples with growth of probable contaminants"  # noqa: E501
            ).format(sample_type)]
            row_2 = [_("Total number {} samples tested").format(sample_type)]
            row_3 = [_("Contamination rate (%) - {}").format(sample_type)]
            for month in range(1, 13):
                num_samples = counted_samples.get(month, 0)
                num_contamination = count_contamination.get(month, 0)
                row_1.append(num_contamination)
                row_2.append(num_samples)
                row_3.append(calculate_rate(num_samples, num_contamination))
            rows.extend([row_1, row_2, row_3])

        months = [MONTHS[num] for num in range(1, 13)]
        headers = [""] + months
        rows.insert(0, headers)
        return rows
