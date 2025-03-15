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

from bes.lims.browser.departmentfilter import get_allowed_departments
from bes.lims.browser.departmentfilter import get_selected_departments
from bes.lims.browser.departmentfilter import NO_DEPARTMENT
from bes.lims.browser.departmentfilter import set_selected_departments
from bes.lims.i18n import translate as t
from bes.lims import _
from bika.lims import api
from plone.app.layout.viewlets import ViewletBase
from plone.memoize import view
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


class DepartmentFilteringViewlet(ViewletBase):
    """ Print a viewlet to display the department filtering bar
    """
    index = ViewPageTemplateFile("templates/departmentfilter.pt")

    def get_current_contact(self):
        """Returns the laboratory contact that is linked to the current user,
        if any. Returns None otherwise
        """
        user = api.get_current_user()
        return api.get_user_contact(user, contact_types="LabContact")

    def get_department_info(self, department):
        """Returns a dict representing a department object
        """
        if department == NO_DEPARTMENT:
            return {
                "uid": NO_DEPARTMENT,
                "title": t(_("No department")),
                "path": "",
                "url": "",
                "css": "text-secondary"
            }

        department = api.get_object(department)
        return {
            "uid": api.get_uid(department),
            "title": api.to_utf8(api.get_title(department)),
            "path": api.get_path(department),
            "url": api.get_url(department),
            "css": "",
        }

    @view.memoize
    def get_departments(self):
        """"Returns a list of dicts with the information of the available
        departments and those that are selected for the laboratory contact
        linked to the current user
        """
        contact = self.get_current_contact()
        if not contact:
            return []

        # departments allowed for the current user
        allowed = get_allowed_departments(contact)

        # departments selected for the current user
        selected = get_selected_departments(contact)

        departments = []
        for uid in allowed:
            info = self.get_department_info(uid)
            info["selected"] = uid in selected
            departments.append(info)

        return departments

    def is_visible(self):
        """Returns whether this viewlet is visible or not
        """
        departments = self.get_departments()
        return True if departments else False

    def render(self):
        # Check if form was submitted
        form_submitted = (
            "departments" in self.request.form
            or "all_departments" in self.request.form
        )
        if not form_submitted:
            return self.index()

        contact = self.get_current_contact()

        all_departments = self.request.form.get("all_departments", None)
        if all_departments:
            # Get all available departments
            departments = get_allowed_departments(contact)
        else:
            # Otherwise use the selected departments
            departments = self.request.form.get("departments", [])

        set_selected_departments(contact, departments)

        return self.index()
