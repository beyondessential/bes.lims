# -*- coding: utf-8 -*-

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
        # Handle manual selection of departments
        departments = self.request.form.get("departments", None)
        if departments is None:
            return self.index()

        contact = self.get_current_contact()
        set_selected_departments(contact, departments)

        return self.index()
