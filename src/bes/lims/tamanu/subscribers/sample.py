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

from bes.lims.tamanu.subscribers.arreport import send_diagnostic_report


def on_after_transition(sample, event):  # noqa camelcase
    """Actions to be done when a transition for a sample takes place
    """
    if not event.transition:
        return

    # get the last report for this sample, if any
    report = get_last_report(sample)

    # notify tamanu back about this report status
    send_diagnostic_report(sample, report)


def get_last_report(sample):
    """Returns the last analysis report that was created for this sample
    """
    reports_ids = sample.objectIds("ARReport")
    if not reports_ids:
        return None
    return sample.get(reports_ids[-1])
