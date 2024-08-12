# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# Copyright 2024 Beyond Essential Systems Pty Ltd

from bes.lims import messageFactory as _
from bes.lims.config import MONTHS
from bes.lims.reports import count_by
from bes.lims.reports import get_received_samples_by_year
from bes.lims.reports import group_by
from bes.lims.reports.forms import CSVReport


class SamplesReceivedByMonth(CSVReport):
    """Samples received by month
    """

    def process_form(self):
        # get the received samples within the given year
        year = int(self.request.form.get("year"))
        brains = get_received_samples_by_year(year)

        # add the first row (header)
        months = [MONTHS[num] for num in range(1, 13)]
        rows = [[_("Sample type")] + months]

        # group the samples by type
        samples_by_type = group_by(brains, "getSampleTypeTitle")

        # sort sample types alphabetically ascending
        sample_types = sorted(samples_by_type.keys())

        for sample_type in sample_types:

            # group and count the samples by reception date
            samples = samples_by_type[sample_type]
            counts = count_by(samples, "getDateReceived")

            # get the samples count for each registered month
            sample_counts = map(lambda mth: counts.get(mth, 0), range(1, 13))

            # build the row
            rows.append([sample_type] + sample_counts)

        return rows
