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

from bes.lims import logger
from bes.lims.browser.departmentfilter import get_selected_departments
from bes.lims.browser.departmentfilter import NO_DEPARTMENT
from bika.lims import api
from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from zope.component import adapter
from zope.interface import implementer
from plone.memoize import view

DEPARTMENT_UID_IDX = "department_uid"


@adapter(IListingView)
@implementer(IListingViewAdapter)
class DepartmentFilterListingAdapter(object):
    """A listing adapter that filters items in the listing based on the
    department(s) selected by the current user.

    If the user has not selected any departments, the adapter defaults to
    filtering items based on the user's default department.
    """

    # Order of priority of this subscriber adapter over others
    priority_order = 9999

    def __init__(self, listing, context):
        self.listing = listing
        self.context = context

    def before_render(self):
        # get the department filter specific query
        query = self.get_department_filter_query()
        if query:
            # update the content filter for all review states
            self.update_content_filter(query)

    def folder_item(self, obj, item, index):
        return item

    def get_current_contact(self):
        """Returns the laboratory contact that is linked to the current user,
        if any
        """
        user = api.get_current_user()
        return api.get_user_contact(user, contact_types="LabContact")

    @view.memoize
    def get_department_filter_query(self):
        """Returns the query to filter the results by the department(s) that
        are available or selected for the laboratory contact linked to the
        current user. Returns an empty dict if the current user is not linked
        to any contact or department_uid index is missing in current catalog
        """
        cat = api.get_tool(self.listing.catalog)
        idx = cat.Indexes.get(DEPARTMENT_UID_IDX, None)
        if not idx:
            logger.warn("Index '%s' is missing: %s" %
                        (DEPARTMENT_UID_IDX, cat.id))
            return {}

        # get the contact linked to the current user
        contact = self.get_current_contact()
        if not contact:
            return {}

        # get the departments selected/supported by current contact
        uids = get_selected_departments(contact)

        # handle empty department properly
        uids = map(lambda uid: "" if uid == NO_DEPARTMENT else uid, uids)

        # build the query
        query = {DEPARTMENT_UID_IDX: uids}
        if idx.meta_type == "KeywordIndex":
            query = {
                DEPARTMENT_UID_IDX: {
                    "query": uids,
                    "operator": "or"
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
