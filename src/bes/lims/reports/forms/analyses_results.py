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
from collections import OrderedDict
from datetime import datetime

from bes.lims import messageFactory as _
from bes.lims.exceptions import TooManyRecordsError
from bes.lims.reports import get_analyses
from bes.lims.reports.forms import CSVReport
from bes.lims.setuphandlers import deactivate
from bes.lims.utils import is_reportable
from bika.lims import api
from bika.lims.utils import format_supsub
from bika.lims.utils import to_utf8
from senaite.core.api import dtime
from senaite.core.catalog import SAMPLE_CATALOG
from senaite.core.i18n import translate
from senaite.patient.api import get_age_ymd
from senaite.patient.config import SEXES


class AnalysesResults(CSVReport):
    """Analyses by result, category and department
    """

    def __init__(self, context, request):
        super(AnalysesResults, self).__init__(context, request)

        # max analyses search
        self.max_records = 100000

        # initialize the columns
        self.columns = OrderedDict((
            ("sample_id", {
                "title": _("Sample ID"),
            }),
            ("sample_type", {
                "title": _("Sample Type"),
            }),
            ("age", {
                "title": _("Patient Age"),
            }),
            ("gender", {
                "title": _("Patient Gender"),
            }),
            ("collected", {
                "title": _("Test Date and Time Collected"),
            }),
            ("captured", {
                "title": _("Test Date and Time Tested"),
            }),
            ("verified", {
                "title": _("Test Date and Time Verified"),
            }),
            ("department", {
                "title": _("Test Department"),
            }),
            ("panels", {
                "title": _("Test Panels"),
            }),
            ("test_type", {
                "title": _("Test Type"),
            }),
            ("result", {
                "title": _("Test Result"),
            }),
            ("unit", {
                "title": _("Test Unit"),
            }),
            ("site", {
                "title": _("Site"),
            }),
            ("ward", {
                "title": _("Ward"),
            })
        ))

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

        # Generate one row per analysis
        rows = []
        for brain in brains:
            row = self.get_row(brain)
            if not row:
                continue

            rows.append(row)
            if len(rows) > self.max_records:
                raise TooManyRecordsError(
                    "Too many records (> %s). Please, refine your search" %
                    self.max_records
                )

        # Insert the header row at first position
        rows.insert(0, self.get_header_row())

        return list(filter(None, rows))

    def get_header_row(self):
        """Returns a plain list with the column names
        """
        return [self.columns[key].get("title") for key in self.columns.keys()]

    def get_row(self, analysis):
        """Return a plain list with the column values for the given analysis
        """
        analysis = api.get_object(analysis)
        if not is_reportable(analysis):
            analysis._p_deactivate()
            return None

        info = self.get_row_info(analysis)
        analysis._p_deactivate()
        return [info.get(key, "") for key in self.columns.keys()]

    def get_row_info(self, analysis):
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

        # get the patient's gender/sex
        gender = dict(SEXES).get(sample.getSex())
        gender = translate(gender) if gender else ""

        # get the ward
        ward = self.get_ward(sample)
        ward = api.get_title(ward) if ward else ""

        # add the info for each analysis in a row
        return {
            "sample_id": analysis.getRequestID(),
            "sample_type": sample.getSampleTypeTitle() or "",
            "age": age,
            "gender": gender,
            "collected": sampled,
            "captured": result_captured,
            "verified": result_verified,
            "department": department,
            "panels": ", ".join(profiles),
            "test_type": self.get_analysis_fullname(analysis),
            "result": result,
            "unit": unit,
            "site": sample.getClientTitle() or "",
            "ward": ward,
        }

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

    def get_ward(self, sample):
        # TODO Remove after Wards are ported to bes.lims
        accessor = getattr(sample, "getWard", None)
        if callable(accessor):
            return accessor()
        return None

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

    def get_analysis_fullname(self, analysis):
        """Returns a string that in the format "<name> (keyword)"
        """
        name = api.get_title(analysis)
        if api.is_brain(analysis):
            keyword = analysis.getKeyword
        else:
            keyword = analysis.getKeyword()
        return "%s (%s)" % (name, keyword)
