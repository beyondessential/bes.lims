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
        return datetime_from.split(" ")[1] if " " in datetime_from else ""

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
        return datetime_to.split(" ")[1] if " " in datetime_to else ""

    @view.memoize
    def get_date_types(self):
        """Return the list of Date Types
        """
        return DATE_TYPES

    def is_filter_enabled(self):
        """Check if the filter is currently enabled"""
        # Always check if checkbox is present in form when form is submitted
        if self.request.form:
            return "filter_enabled" in self.request.form

        # For initial load, default to disabled (unchecked)
        return False

    def render(self):
        # Always process form if any form data is present
        if not self.request.form:
            return self.index()

        # Check if filter is enabled (checkbox checked)
        filter_enabled = "filter_enabled" in self.request.form

        if not filter_enabled:
            # Filter is disabled, clear the session with empty values
            set_selected_date_range("", "", "created")
        else:
            # Filter is enabled, process the form data
            date_from = self.request.form.get("date_from", "")
            date_to = self.request.form.get("date_to", "")
            time_from = self.request.form.get("time_from", "")
            time_to = self.request.form.get("time_to", "")
            date_type = self.request.form.get("date_type", "created")

            # Combine date and time into datetime strings
            datetime_from = "{} {}".format(date_from, time_from).strip()
            datetime_to = "{} {}".format(date_to, time_to).strip()

            # Save the selected date range
            set_selected_date_range(datetime_from, datetime_to, date_type)

        return self.index()
