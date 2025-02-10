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
from bes.lims.reports import get_received_samples
from bes.lims.reports.forms import CSVReport
from bika.lims import api
from bika.lims.browser import ulocalized_time
from bika.lims.workflow import getTransitionDate


class SamplesRejectedSummary(CSVReport):
    """Samples rejected summary
    """

    def process_form(self):
        # get the rejected samples within the period
        dt_from = self.request.form.get("date_from")
        dt_to = self.request.form.get("date_to")
        brains = get_received_samples(dt_from, dt_to, review_state="rejected")

        # generate the rows
        rows = map(self.to_row, brains)

        # insert the first row (header)
        header = [
            _("Sample ID"),
            _("Client Name"),
            _("Referring Doctor"),
            _("Sample Type"),
            _("Sample Received Date"),
            _("Sample Rejection Date"),
            _("Reason For Rejection"),
        ]
        rows.insert(0, header)
        return rows

    def to_row(self, sample):
        """Returns a row representing the sample passed-in
        """
        sample = api.get_object(sample)

        # Reasons for rejection
        reasons = ", ".join(sample.getSelectedRejectionReasons())
        other = sample.getOtherRejectionReasons()
        if other:
            reasons = reasons + ", " + other if reasons else other

        return [
            sample.getId(),
            sample.getClientTitle(),
            sample.getContactFullName(),
            sample.getSampleTypeTitle(),
            ulocalized_time(
                sample.getDateReceived(),
                long_format=True,
                time_only=False, context=sample
            ),
            getTransitionDate(sample, 'reject'),
            reasons,
        ]
