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

import pytz
from bes.lims.browser.daterangefilter import get_selected_date_range_config
from bika.lims import api
from plone.memoize import view
from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from senaite.core.api import dtime
from zope.component import adapter
from zope.interface import implementer


def get_timezone():
    """Return the effective timezone for the current user.
    Prefer the user's timezone if set and valid, otherwise fall back to the
    site timezone, and finally to the system (OS) timezone.
    """
    # User's default TZ has priority over portal's
    user = api.get_current_user()
    tz = user.getProperty("timezone")
    if dtime.is_valid_timezone(tz):
        return tz

    # get the portal's default timezone
    tz = api.get_registry_record("plone.portal_timezone")
    if dtime.is_valid_timezone(tz):
        return tz

    # No TZ set or not valid, return OS's
    return dtime.get_os_timezone()


@adapter(IListingView)
@implementer(IListingViewAdapter)
class DateRangeFilterListingAdapter(object):
    """A listing adapter that filters items in the listing based on the
    date range selected.
    """

    # Order of priority of this subscriber adapter over others
    priority_order = 9999

    def __init__(self, listing, context):
        self.listing = listing
        self.context = context

    def before_render(self):
        # Get the date range filter specific query
        query = self.get_date_range_filter_query()
        if query:
            # update the content filter for all review states
            self.update_content_filter(query)

    def folder_item(self, obj, item, index):
        return item

    @view.memoize
    def get_date_range_filter_query(self):
        """Returns a query dict to filter results by the selected date range
        """

        # get the date range selected for current contact
        date_range = get_selected_date_range_config()

        # Check if filter is enabled
        if not date_range.get("filter_enabled", False):
            return {}

        # get the date range and index name to search by (date_type)
        dt_from = dtime.to_dt(date_range.get("datetime_from"))
        dt_to = dtime.to_dt(date_range.get("datetime_to"))
        date_type = date_range.get("date_type")
        if not all([dt_from, dt_to, date_type]):
            return {}

        # Dates submitted with the form are timezone-naive. We therefore
        # explicitly set (without shifting the time value) the current
        # user/site/system timezone so that searches align with the timezone
        # used during indexing.
        timezone = get_timezone()
        tz_info = pytz.timezone(timezone)
        dt_from = dt_from.replace(tzinfo=tz_info)
        dt_to = dt_to.replace(tzinfo=tz_info)

        # convert to Zope's DateTime
        dt_from = dtime.to_DT(dt_from)
        dt_to = dtime.to_DT(dt_to)

        # build the query - filter by the selected date type
        query = {
            date_type: {
                "query": [dt_from, dt_to],
                "range": "min:max"
            }
        }
        return query

    def update_content_filter(self, query):
        """Updates the listing content filter with the query passed in
        """
        self.listing.contentFilter.update(query)
        for review_state in self.listing.review_states:
            if "contentFilter" not in review_state:
                review_state["contentFilter"] = {}
            review_state["contentFilter"].update(query)
        self.listing.contentFilter.update(query)
