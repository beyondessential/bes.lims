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

import re
from datetime import datetime

from bes.lims import messageFactory as _
from bes.lims.reports import get_analyses
from bes.lims.reports.forms import CSVReport
from bes.lims.utils import is_reportable
from bika.lims import api
from senaite.core.api import dtime
from senaite.core.catalog import SAMPLE_CATALOG
from senaite.patient.config import SEXES


class AnalysesResults(CSVReport):
    """Analyses by result, category and department
    """

    def process_form(self):
        statuses = ["published"]
        # Collect the analyses filters (date received)
        date_from, date_to = self.parse_date_for_query()

        # search by requested department
        department_uid = self.request.form.get("department")
        brains = get_analyses(date_from, date_to, review_state=statuses,
                              department_uid=department_uid)
        objs = map(api.get_object, brains)
        analyses = [analysis for analysis in objs if is_reportable(analysis)]

        # Add the first row (header)
        rows = [[
            _("Sample ID"),
            _("Patient Name"),
            _("Patient Surname"),
            _("Patient Other Names"),
            _("Patient Hospital #"),
            _("Patient Date of Birth"),
            _("Patient Gender"),
            _("Test Date Collected"),
            _("Test Date Tested"),
            _("Test Category"),
            _("Test Department"),
            _("Test ID"),
            _("Test Type"),
            _("Test Result"),
            _("Site"),
            _("Requesting Physician"),
        ]]

        # Add the info per analysis in a row
        for analysis in analyses:
            sample = analysis.getRequest()
            fullname = sample.getField("PatientFullName").get(sample) or {}
            dob = self.parse_date_to_output(sample.getDateOfBirth()[0])
            sampled = self.parse_date_to_output(sample.getDateSampled())
            result_captured = self.parse_date_to_output(
                analysis.getResultCaptureDate()
            )

            # Only show results that appear on the final reports
            result = ""
            if analysis.getDatePublished():
                result = analysis.getFormattedResult(html=False) or result
                result = self.replace_html_breaklines(result)

            department = analysis.getDepartmentTitle() or ""
            category = analysis.getCategoryTitle() or ""

            # add the info for each analysis in a row
            rows.append(
                [
                    analysis.getRequestID(),
                    fullname.get("firstname", ""),
                    fullname.get("lastname", ""),
                    fullname.get("middlename", ""),
                    sample.getMedicalRecordNumberValue() or "",
                    dob,
                    dict(SEXES).get(sample.getSex(), ""),
                    sampled,
                    result_captured,
                    category,
                    department,
                    analysis.getKeyword(),
                    analysis.Title(),
                    result,
                    sample.getClientTitle() or "",
                    sample.getContactFullName() or "",
                ]
            )

        return rows

    def replace_html_breaklines(self, text, replacement="; "):
        regex = r'<br\s*\/?>|<BR\s*\/?>'
        return re.sub(regex, replacement, text)

    def parse_date_for_query(self):
        # Get earliest possible date (first sample date)
        date0 = self.get_first_sample_date()

        # Get latest possible date (today)
        current_date = datetime.now()

        # Set date range
        date_from = self.request.form.get('date_from') or date0
        date_to = self.request.form.get('date_to') or current_date

        # Parse dates for query
        date_from = dtime.to_DT(date_from).earliestTime()
        date_to = dtime.to_DT(date_to).latestTime()

        return date_from, date_to

    def get_first_sample_date(self):
        query = {
            "portal_type": "AnalysisRequest",
            "sort_on": "created",
            "sort_order": "ascending",
            "sort_limit": 1,
        }
        brains = api.search(query, SAMPLE_CATALOG)
        year = brains[0].created.year()
        return datetime(year, 1, 1)

    def parse_date_to_output(self, date):
        return dtime.to_localized_time(date, long_format=False) or ""
