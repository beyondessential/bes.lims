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


from datetime import datetime

from bes.lims.config import TARGET_PATIENTS
from bika.lims import api
from plone.memoize import view
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile as PT
from senaite.app.supermodel import SuperModel
from senaite.core.catalog import SAMPLE_CATALOG
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.workflow import ANALYSIS_WORKFLOW
from senaite.core.api import workflow as wapi

YEAR_CONTROL = "controls/year.pt"
DATE_CONTROL = "controls/date.pt"
TARGET_PATIENT_CONTROL = "controls/target_patient.pt"
DEPARTMENT_CONTROL = "controls/department.pt"
ANALYSIS_STATES_CONTROL = "controls/analysis_states.pt"


class StatisticReportsView(BrowserView):
    """Statistics view form
    """
    template = PT("templates/statistic_reports.pt")

    def __call__(self):
        form = self.request.form

        submit = form.get("submit")
        report_id = form.get("report_id")

        if submit and report_id:
            report_form = api.get_view(report_id)
            return report_form()

        return self.template()

    def year_control(self):
        """Returns the control for year selection
        """
        return PT(YEAR_CONTROL)(self)

    def date_control(self):
        """Returns the control for date selection
        """
        return PT(DATE_CONTROL)(self)

    def target_patient_control(self):
        """Returns the control for year selection
        """
        return PT(TARGET_PATIENT_CONTROL)(self)

    def department_control(self):
        """Returns the control for department selection
        """
        return PT(DEPARTMENT_CONTROL)(self)

    def analysis_states_control(self):
        """Returns the control for the selection of analysis states
        """
        return PT(ANALYSIS_STATES_CONTROL)(self)

    @view.memoize
    def get_years(self):
        """Returns the list of years since the first sample was created
        """
        query = {
            "portal_type": "AnalysisRequest",
            "sort_on": "created",
            "sort_order": "ascending",
            "sort_limit": 1,
        }

        since = datetime.now().year
        brains = api.search(query, SAMPLE_CATALOG)
        if brains:
            since = brains[0].created.year()

        current = datetime.now().year
        return range(since, current+1)

    @view.memoize
    def get_departments(self):
        """Returns the list of available departments
        """
        query = {
            "portal_type": "Department",
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        }
        brains = api.search(query, SETUP_CATALOG)
        return [SuperModel(brain) for brain in brains]

    @view.memoize
    def get_analysis_states(self):
        """Returns the list of analysis statuses that are suitable for
        reporting, as tuples of (state_id, state_title): verified,
        to_be_verified, published and out_of_stock
        """
        supported = ["to_be_verified", "verified", "published", "out_of_stock"]
        wf = wapi.get_workflow(ANALYSIS_WORKFLOW)
        return [(state, wf.getTitleForStateOnType(state, "Analysis"))
                for state in supported]

    def get_target_patients(self):
        """Returns the list target patient
        """
        return TARGET_PATIENTS

    def render_report_section(self, report_id):
        """Renders the report section with the given id
        """
        template_path = "templates/{}.pt".format(report_id)
        template = PT(template_path)
        return template(self)

    @property
    def date_from(self):
        """Returns the first date of selected duration
        """
        # Default to first day of current month
        default = datetime.now()
        default = datetime(default.year, default.month, 1)
        date_from = self.request.form.get("date_from", None)
        date_from = api.to_date(date_from, default=default)
        return date_from.strftime("%Y-%m-%d")

    @property
    def date_to(self):
        """Returns the last date of selected duration
        """
        date_to = self.request.form.get("date_to", None)
        date_to = api.to_date(date_to, default=datetime.now())
        return date_to.strftime("%Y-%m-%d")
