# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# Copyright 2024 Beyond Essential Systems Pty Ltd

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
        # verified and published samples that were received within a given year
        statuses = ["to_be_verified", "verified", "published"]
        # skip AST-like analyses
        poc = ["lab", "field"]
        # search by requested year
        year = int(self.request.form.get("year"))
        # search by requested department
        department_uid = self.request.form.get("department")
        brains = get_analyses_by_year(year, review_state=statuses,
                                      department_uid=department_uid,
                                      getPointOfCapture=poc)

        # add the first two rows (header)
        department = api.get_object_by_uid(department_uid, default=None)
        department_name = api.get_title(department) if department else ""
        months = [MONTHS[num] for num in range(1, 13)]
        rows = [[department_name] + months + [_("Total")]]

        # keep a dict to store the totals per month
        totals_by_month = OrderedDict.fromkeys(range(1, 14), 0)

        # group the analyses brains by title
        analyses_by_title = group_by(brains, "Title")

        # get titles and sort them
        titles = sorted(analyses_by_title.keys())

        for title in titles:

            # get the analyses for the test with the given title
            analyses = analyses_by_title[title]

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
            rows.append([title] + analysis_counts + [total])

        # build the totals by month row
        rows.append([_("Total")] + totals_by_month.values())

        return rows
