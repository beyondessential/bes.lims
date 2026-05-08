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

from bika.lims import api
from bes.lims import _
from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from senaite.core.browser.controlpanel.analysisprofiles.view import get_link_for
from zope.component import adapts
from zope.interface import implements


class AnalysisProfilesListingAdapter(object):
    """Adapter for analysis profiles listings
    """
    adapts(IListingView)
    implements(IListingViewAdapter)

    # Priority order of this adapter over others
    priority_order = 9999


    def __init__(self, listing, context):
        self.listing = listing
        self.context = context

    def before_render(self):
        self.listing.columns["ProfileAnalyses"] = {
            "title": _("Profile Analyses"),
            "toggle": True,
        }
        for review_state in self.listing.review_states:
            review_state["columns"] = self.listing.columns.keys()

    def folder_item(self, obj, item, index):
        profile = api.get_object(obj)
        analyses = profile.getServices()
        titles = map(api.get_title, analyses)
        links = map(get_link_for, analyses)
        item["ProfileAnalyses"] = ", ".join(titles)
        item["replace"]["ProfileAnalyses"] = ", ".join(links)
        return item
