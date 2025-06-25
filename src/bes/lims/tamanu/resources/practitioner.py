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

from bes.lims.tamanu.resources import TamanuResource
from bes.lims.tamanu.hl7.datatypes.humanname import HumanName

_marker = object()


class Practitioner(TamanuResource):
    """Object that represents a Practitioner resource from Tamanu
    """

    def get_emails(self):
        """Returns the emails assigned to this resource
        """
        emails = []
        records = self.get("telecom") or []
        for telecom in records:
            if telecom.get("system") != "email":
                continue
            email = telecom.get("email")
            if email not in emails:
                emails.append(email)
        return filter(None, emails)

    def _get_name(self):
        """Resolves the value for the field 'name'
        """
        names = self.get_raw("name", [])
        return map(HumanName, names)

    def get_name_record(self, use):
        """Returns the name HL7 record for the given use (e.g. 'official')
        """
        for name in self._get_name():
            if name.get("use") == use:
                return name
        return None

    def get_name_info(self):
        """Returns a dict with the name parts
        """
        base_info = {
            "Salutation": "",
            "Firstname": "",
            "Middleinitial": "",
            "Middlename": "",
            "Surname": "",
        }

        # try with the official name first
        name = self.get_name_record("official")
        if name:
            base_info.update(name.get_name_info())
            return base_info

        # pick the first one
        names = self._get_name()
        if names:
            base_info.update(names[0].get_name_info())
            return base_info

        return base_info

    def to_object_info(self):
        """Returns a dict representation of the Practitioner resource, suitable
        for the creation and edition of SENAITE's Person objects like Contact,
        LabContact, etc.
        """
        # TODO pick the first email address as default
        emails = self.get_emails()
        email = emails[0] if emails else ""

        info = {
            "EmailAddress": email,
            "BusinessPhone": "",
            "BusinessFax": "",
            "HomePhone": "",
            "MobilePhone": "",
            "JobTitle": "",
            "Department": "",
            "PhysicalAddress": {},
            "PostalAddress": {},
        }

        # Fill with HumanName info
        name_info = self.get_name_info()
        info.update(name_info)
        return info
