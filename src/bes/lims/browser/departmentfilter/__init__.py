# -*- coding: utf-8 -*-

from bika.lims import api
from persistent.list import PersistentList
from senaite.core.catalog import SETUP_CATALOG
from zope.annotation.interfaces import IAnnotations

STORAGE_KEY = "departmentfilter.storage"

NO_DEPARTMENT = "--NODEPARTMENT--"


def is_lab_manager(contact):
    """Returns whether the current contact is a manager or lab manager
    """
    manager_roles = ["LabManager", "Manager"]
    user = contact.getUser()
    roles = user.getRoles() if user else []
    for role in roles:
        if role in manager_roles:
            return True
    return False


def get_allowed_departments(contact):
    """Returns the UIDs of the departments associated with this contact.

    If the lab contact is not assigned to any specific department, the function
    assumes the contact has access to all active departments and returns the
    complete list.
    """
    departments = contact.getRawDepartments()
    if not departments:
        # assume this contact can see all active departments
        query = {"portal_type": "Department", "is_active": True}
        brains = api.search(query, SETUP_CATALOG)
        departments = list(map(api.get_uid, brains))

    # samples without department are allowed too
    departments.append(NO_DEPARTMENT)

    return departments


def get_selected_departments(contact):
    """Returns the UIDs of the departments currently selected for the contact.

    If no departments were explicitly selected for this contact in the UI, the
    function defaults to returning the UIDs of all departments associated with
    the contact.
    """
    # get the departments associated with this contact
    departments = get_allowed_departments(contact)

    # get the departments storage for this contact
    annotations = IAnnotations(contact)
    if annotations.get(STORAGE_KEY) is None:
        annotations[STORAGE_KEY] = PersistentList(departments)

    # purge the departments this contact does no longer have access to
    selected = list(set(annotations[STORAGE_KEY]))
    return list(filter(lambda dept: dept in departments, selected))


def set_selected_departments(contact, departments):
    """Sets the departments currently selected for the contact
    """
    annotations = IAnnotations(contact)
    annotations[STORAGE_KEY] = PersistentList(set(departments))
