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

from bes.lims.browser.daterangefilter import get_selected_date_range
from bes.lims.browser.daterangefilter import set_selected_date_range
from bes.lims.config import DATE_TYPES
from datetime import datetime
from plone.app.layout.viewlets import ViewletBase
from plone.memoize import view
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


class DateRangeFilteringViewlet(ViewletBase):
    """ Print a viewlet to display the date range filtering bar
    """
    index = ViewPageTemplateFile("templates/daterangefilter.pt")

    @view.memoize
    def get_date_range(self):
        """Returns the selected date range
        """
        return get_selected_date_range()

    def get_date_from(self):
        """Extract date part from datetime_from"""
        datetime_from = self.get_date_range().get("datetime_from", "")
        return datetime_from.split(" ")[0] if datetime_from else ""

    def get_time_from(self):
        """Extract time part from datetime_from"""
        datetime_from = self.get_date_range().get("datetime_from", "")
        return datetime_from.split(" ")[1] if " " in datetime_from else "00:00"

    def get_date_to(self):
        """Extract date part from datetime_to"""
        datetime_to = self.get_date_range().get("datetime_to", "")
        return datetime_to.split(" ")[0] if datetime_to else ""

    def get_date_type(self):
        """Returns the selected date type"""
        return self.get_date_range().get("date_type", "created")

    def get_time_to(self):
        """Extract time part from datetime_to"""
        datetime_to = self.get_date_range().get("datetime_to", "")
        return datetime_to.split(" ")[1] if " " in datetime_to else "23:59"

    @view.memoize
    def get_date_types(self):
        """Return the list of Date Types
        """
        return DATE_TYPES

    def render(self):
        # Check if the form was submitted
        form_submitted = (
            "date_from" in self.request.form
            or "date_to" in self.request.form
            or "time_from" in self.request.form
            or "time_to" in self.request.form
            or "date_type" in self.request.form
        )
        if not form_submitted:
            return self.index()

        # Get the submitted date range, time range and type
        date_from = self.request.form.get("date_from")
        date_to = self.request.form.get("date_to")
        time_from = self.request.form.get("time_from")
        time_to = self.request.form.get("time_to")
        date_type = self.request.form.get("date_type")

        # Validate and set default dates if empty
        if not date_from or not date_to:
            now = datetime.now()
            first_day = datetime(now.year, now.month, 1)
            date_from = date_from or first_day.strftime("%Y-%m-%d")
            date_to = date_to or now.strftime("%Y-%m-%d")

        # Combine date and time into datetime strings
        datetime_from = "{} {}".format(date_from, time_from)
        datetime_to = "{} {}".format(date_to, time_to)

        # Save the selected date range
        set_selected_date_range(datetime_from, datetime_to, date_type)

        return self.index()
