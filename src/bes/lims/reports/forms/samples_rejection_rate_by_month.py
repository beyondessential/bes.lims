# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# Copyright 2024 Beyond Essential Systems Pty Ltd

from bes.lims import messageFactory as _
from bes.lims.config import MONTHS
from bes.lims.reports import count_by
from bes.lims.reports import get_percentage
from bes.lims.reports import get_received_samples_by_year
from bes.lims.reports.forms import CSVReport


class SamplesRejectionRateByMonth(CSVReport):
    """Samples rejected by month
    """

    def process_form(self):
        # get the received and rejected samples within the given year
        year = int(self.request.form.get("year"))
        received = get_received_samples_by_year(year)
        rejected = get_received_samples_by_year(year, review_state="rejected")

        # group and count samples by reception date
        count_received = count_by(received, "getDateReceived")
        count_rejected = count_by(rejected, "getDateReceived")

        rows = []
        row_received = [_("Total samples received")]
        row_rejected = [_("Total samples rejected")]
        row_rate = [_("Sample rejection rate (%)")]
        for month in range(1, 13):
            num_received = count_received.get(month, 0)
            num_rejected = count_rejected.get(month, 0)
            rate = get_percentage(num_rejected, num_received)

            row_received.append(num_received)
            row_rejected.append(num_rejected)
            row_rate.append(rate)

        rows.extend([row_received, row_rejected, row_rate])

        months = [MONTHS[num] for num in range(1, 13)]
        headers = [""] + months
        rows.insert(0, headers)
        return rows
