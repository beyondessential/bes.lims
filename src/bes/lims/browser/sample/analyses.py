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

import collections

from bes.lims import messageFactory as _
from bika.lims import api
from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from senaite.app.listing.utils import add_review_state
from zope.component import adapter
from zope.interface import implementer

# Statuses to add. List of dicts
ADD_STATUSES = [
    {
        "id": "out_of_stock",
        "title": _("Out of stock"),
        "contentFilter": {
            "review_state": "out_of_stock",
            "sort_on": "sortable_title",
            "sort_order": "ascending",
        },
        "after": "invalid",
    },
]


@adapter(IListingView)
@implementer(IListingViewAdapter)
class SampleAnalysesListingAdapter(object):
    """Adapter for analyses listings
    """

    # Priority order of this adapter over others
    priority_order = 99999

    def __init__(self, listing, context):
        self.listing = listing
        self.context = context

    def folder_item(self, obj, item, index):
        self.render_results_range(obj, item)
        return item

    def render_results_range(self, obj, item):
        """Sets the results range to the item passed in
        """
        analysis = self.listing.get_object(obj)

        # use listing's default if value for max is above 0
        specs = analysis.getResultsRange()
        range_max = api.to_float(specs.get("max"), default=0)
        if range_max > 0:
            return

        # no value set for neither min nor max, show the range comment
        comment = specs.get("rangecomment")
        if comment:
            item["replace"]["Specification"] = comment

    def before_render(self):
        # Move "Analyst" and "Status" columns to the end, before "Due date"
        self.move_column("Analyst", before="DueDate")
        self.move_column("state_title", after="Analyst")

        # Add review_states
        for status in ADD_STATUSES:
            after = status.get("after", None)
            before = status.get("before", None)
            if not status.get("columns"):
                status.update({"columns": self.listing.columns.keys()})
            add_review_state(self.listing, status, after=after, before=before)

        # Rename the column "Specification" to "Normal values"
        for key, value in self.listing.columns.items():
            if key == "Specification":
                value["title"] = _(
                    u"title_column_specification_analyses",
                    default=u"Normal value")

    def move_column(self, column_id, before=None, after=None):
        """Moves the column with the id passed in to the new position
        """
        column = self.listing.columns.pop(column_id)
        out_columns = collections.OrderedDict()
        for key, item in self.listing.columns.items():
            if before == key:
                out_columns[column_id] = column
            out_columns[key] = item
            if after == key:
                out_columns[column_id] = column
        self.listing.columns = out_columns

        for state in self.listing.review_states:
            rv_state = state.copy()
            cols = rv_state.get("columns", [])
            if column_id not in cols:
                continue
            cols.remove(column_id)
            idx = len(cols)
            if before in cols:
                idx = cols.index(before)
            elif after in cols:
                idx = cols.index(after) + 1

            cols.insert(idx, column_id)
