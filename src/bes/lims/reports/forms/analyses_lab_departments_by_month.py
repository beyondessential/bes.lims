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
from bes.lims.config import MONTHS
from bes.lims.reports import count_by
from bes.lims.reports import get_analyses_by_year
from bes.lims.reports import group_by
from bes.lims.reports.forms import CSVReport
from bika.lims import api


class AnalysesLabDepartmentsByMonth(CSVReport):
    """Analyses Lab Departments by month
    """

    def process_form(self):
        # analysis states
        statuses = self.request.form.get("analysis_states")
        # skip AST-like analyses
        poc = ["lab", "field"]
        # search by requested year
        year = int(self.request.form.get("year"))
        # search by requested department
        department_uid = self.request.form.get("department")
        query = {"review_state": statuses, "getPointOfCapture": poc}
        if api.is_uid(department_uid):
            query["department_uid"] = department_uid

        # do the search
        brains = get_analyses_by_year(year, **query)

        # add the first two rows (header)
        department = api.get_object_by_uid(department_uid, default=None)
        department_name = api.get_title(department) if department else ""
        months = [MONTHS[num] for num in range(1, 13)]
        rows = [[department_name] + months + [_("Total")]]

        # keep a dict to store the totals per month
        totals_by_month = OrderedDict.fromkeys(range(1, 14), 0)

        # group the analyses brains by title
        analyses_by_name = group_by(brains, self.get_analysis_fullname)

        # get titles and sort them
        names = sorted(analyses_by_name.keys())

        for name in names:

            # get the analyses for the test with the given title
            analyses = analyses_by_name[name]

            # group and count the analyses by reception date
            counts = count_by(analyses, "getDateReceived")

            # counts and total by department
            analysis_counts = map(lambda mth: counts.get(mth, 0), range(1, 13))
            total = sum(analysis_counts)

            # update all totals
            totals_by_month[13] += total

            # update the totals by month
            for month in range(1, 13):
                totals_by_month[month] += counts.get(month, 0)

            # build the totals by analysis name row
            rows.append([name] + analysis_counts + [total])

        # build the totals by month row
        rows.append([_("Total")] + totals_by_month.values())

        return rows

    def get_analysis_fullname(self, analysis):
        """Returns a string that in the format "<name> (keyword)"
        """
        name = api.get_title(analysis)
        if api.is_brain(analysis):
            keyword = analysis.getKeyword
        else:
            keyword = analysis.getKeyword()
        return "%s (%s)" % (name, keyword)
