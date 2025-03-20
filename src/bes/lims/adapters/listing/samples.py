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

from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from zope.component import adapts
from zope.interface import implements

# Statuses to update. List of tuples (status_id, {properties})
UPDATE_STATUSES = [
    ("default", {
        "flat_listing": True,
    }),
    ("sample_due", {
        "flat_listing": True,
    }),
    ("sample_received", {
        "flat_listing": True,
    }),
    ("to_be_verified", {
        "flat_listing": True,
    }),
    ("verified", {
        "flat_listing": True,
    })
]


class SamplesListingAdapter(object):
    """Generic adapter for sample listings
    """
    adapts(IListingView)
    implements(IListingViewAdapter)

    # Priority order of this adapter over others
    priority_order = 9999

    def __init__(self, listing, context):
        self.listing = listing
        self.context = context

    def folder_item(self, obj, item, index):
        return item

    def before_render(self):
        # Update review_states
        states_to_update = dict(UPDATE_STATUSES)
        for rv in self.listing.review_states:
            values = states_to_update.get(rv["id"], {})
            rv.update(values)
