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
from bika.lims.utils import format_supsub
from bika.lims.utils import to_utf8
from senaite.core.api import dtime
from senaite.core.catalog import SAMPLE_CATALOG
from senaite.patient.api import get_age_ymd
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
        query = {"review_state": statuses}
        if api.is_uid(department_uid):
            query["department_uid"] = department_uid

        # do the search
        brains = get_analyses(date_from, date_to, **query)
        objs = map(api.get_object, brains)
        analyses = [analysis for analysis in objs if is_reportable(analysis)]

        # Add the first row (header)
        rows = [[
            _("Sample ID"),
            _("Sample Type"),
            _("Patient Age"),
            _("Patient Gender"),
            _("Test Date and Time Collected"),
            _("Test Date and Time Tested"),
            _("Test Date and Time Verified"),
            _("Test Department"),
            _("Test Panels"),
            _("Test Type"),
            _("Test Result"),
            _("Test Unit"),
            _("Site"),
        ]]

        # Add the info per analysis in a row
        for analysis in analyses:
            sample = analysis.getRequest()
            sampled = sample.getDateSampled()
            dob = sample.getDateOfBirth()[0]
            age = self.get_age(dob, sampled)
            sampled = self.parse_date_to_output(sampled)
            result_captured = self.parse_date_to_output(
                analysis.getResultCaptureDate()
            )
            result_verified = self.parse_date_to_output(
                analysis.getDateVerified()
            )
            # Only show results that appear on the final reports
            result = ""
            if analysis.getDatePublished():
                result = analysis.getFormattedResult(html=False) or result
                result = self.replace_html_breaklines(result)

            # get the department title
            department = analysis.getDepartment()
            department = api.get_title(department) if department else ""

            profiles = self.get_analysis_profiles(sample)
            unit = format_supsub(to_utf8(analysis.Unit))

            # add the info for each analysis in a row
            rows.append(
                [
                    analysis.getRequestID(),
                    sample.getSampleTypeTitle() or "",
                    age,
                    dict(SEXES).get(sample.getSex(), ""),
                    sampled,
                    result_captured,
                    result_verified,
                    department,
                    ", ".join(profiles),
                    analysis.Title(),
                    result,
                    unit,
                    sample.getClientTitle() or "",
                ]
            )

        return rows

    def get_age(self, dob, sampled):
        """Returns the age truncated to the highest period
        """
        ymd = get_age_ymd(dob, sampled)
        if not ymd:
            return None
        # truncate to highest period
        matches = re.match(r"^(\d+[ymd])", ymd)
        return matches.groups()[0]

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
        return dtime.to_localized_time(date, long_format=True) or ""

    def get_analysis_profiles(self, sample):
        profiles = sample.getProfiles()
        return map(api.get_title, profiles)
