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
from bes.lims.reports import group_by
from bes.lims.reports import count_by
from bes.lims.reports.forms import CSVReport
from bika.lims import api
from collections import OrderedDict


class SamplesRejectionByDepartment(CSVReport):
    """Samples rejected by department
    """

    def process_form(self):
        from_date = self.request.form.get("date_from")
        to_date = self.request.form.get("date_to")
        query = {
            "review_state": "rejected",
        }
        brains = get_received_samples(from_date, to_date, **query)
        objs = map(api.get_object, brains)
        rejection_reasons = []
        for obj in objs:
            list_rejection_reasons = obj.getSelectedRejectionReasons()
            map(lambda reason: rejection_reasons.append(reason), list_rejection_reasons)  # noqa: E501
        rejection_reasons = list(
            OrderedDict.fromkeys(sorted(rejection_reasons))
        )
        samples_by_dept = group_by(objs, "getWardDepartment")

        rows = []
        for dept, samples_in_dept in samples_by_dept.items():
            counted_samples_by_rejection_reason = count_by(
                samples_in_dept, "getSelectedRejectionReasons"
            )
            row = [dept]
            for rejection_reason in rejection_reasons:
                value = counted_samples_by_rejection_reason[rejection_reason] \
                    if rejection_reason in counted_samples_by_rejection_reason else 0  # noqa: E501
                row.append(value)
            rows.append(row)

        header_rejection_reasons = [title for title in rejection_reasons]
        headers = [_("Department")] + header_rejection_reasons
        rows.insert(0, headers)

        return rows
