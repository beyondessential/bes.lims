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
from senaite.core.api import dtime
from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from zope.component import adapter
from zope.interface import implementer
from plone.memoize import view


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
        date_range = get_selected_date_range()
        datetime_from = date_range.get("datetime_from")
        datetime_to = date_range.get("datetime_to")
        date_type = date_range.get("date_type")
        if not datetime_from or not datetime_to:
            return {}

        date_from_dt = dtime.to_DT(datetime_from)
        date_to_dt = dtime.to_DT(datetime_to)

        # build the query - filter by the selected date type
        query = {
            date_type: {
                "query": [date_from_dt, date_to_dt],
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
