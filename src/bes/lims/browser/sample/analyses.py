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
from bes.lims.reflex import get_reflex_testing_adapter
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
        self.reload_actions = {}

    def folder_item(self, obj, item, index):
        # render results range or range comment
        self.render_results_range(obj, item)
        # force full view reload if required
        self.render_reload(obj, item)
        return item

    def render_reload(self, obj, item):
        """Assign the item's reload attribute with the actions for the given
        object that required a full-view reload after transition
        """
        # get the actions of this obj that require a full-view reload
        actions = self.get_reload_actions(obj)
        if not actions:
            return

        # maybe reload actions were already set for this obj
        reload_actions = item.get("reload", [])
        reload_actions.extend(actions)
        item["reload"] = list(set(reload_actions))

    def get_reload_actions(self, analysis):
        """Returns a list with the actions for the given analysis that require
        a full-view reload after being triggered
        """
        analysis = self.listing.get_object(analysis)

        # find out if we already know the actions for this keyword
        keyword = analysis.getKeyword()
        actions = self.reload_actions.get(keyword, None)
        if actions is not None:
            return actions

        # loop over reflex-suitable actions
        actions = []
        for action in ["submit", "verify"]:
            ad = get_reflex_testing_adapter(analysis, action)
            if ad:
                actions.append(action)

        # keep a mapping of keyword-to-action
        self.reload_actions[keyword] = actions
        return self.reload_actions.get(keyword)

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

        # Get the listing's review state ids
        states = map(lambda st: st["id"], self.listing.review_states)

        # Add review_states
        for status in ADD_STATUSES:
            # be sure this state exists in listing
            after = status.get("after", None)
            after = after if after in states else None

            # assign the existing columns to the new status
            status.update({"columns": self.listing.columns.keys()})

            # add the review status
            add_review_state(self.listing, status, after=after)

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
