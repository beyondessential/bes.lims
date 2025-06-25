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
from bes.lims.tamanu.config import TAMANU_SEXES
from bes.lims.tamanu.resources import TamanuResource

_marker = object()


class PatientResource(TamanuResource):

    def get_mrn(self):
        identifier = self.get_identifier("usual")
        if not identifier:
            return ""
        return identifier.get("value", "")

    def get_identifier(self, use):
        for identifier in self.get("identifier"):
            if identifier.get("use") == use:
                return identifier
        return None

    def get_fullname(self):
        """Get patient's full name from resource payload
        """
        patient_names = self.get("name")
        fullname = next((
            name for name in patient_names
            if name.get("use") == "official"
        ), None)
        return fullname

    def get_givenname(self):
        """Get patient's given name from full name
        """
        fullname = self.get_fullname()
        if fullname:
            return fullname.get("given", "")
        return ""

    def get_address(self):
        """Get patient's address from resource payload
        """
        patient_addresses = self.get("address")
        address = next((
            patient_address for patient_address in patient_addresses
            if patient_address.get("type") == "physical"
               and patient_address.get("use") == "home"  # noqa
        ), None)
        return address

    def to_object_info(self):
        """Returns a dict representation of the Patient resource, suitable for
        the creation and edition of SENAITE Patient objects
        """
        sexes = dict(TAMANU_SEXES)
        mrn = self.get_mrn()
        sex = sexes.get(self.get("gender")) or ""
        fullname = self.get_fullname()
        givenname = self.get_givenname()
        firstname = givenname[0] if givenname != "" else ""
        middlename = (
            givenname[1]
            if givenname != "" and len(givenname) == 2 else ""
        )
        lastname = fullname.get("family", "")
        birthdate = self.get("birthDate")
        address = self.get_address()

        if address:
            address_line = address.get("line", [""])
            address = list([{
                "type": api.safe_unicode(address.get("type", "")),
                "address": (
                    api.safe_unicode(address_line[0]) if address_line else ""
                ),
                "city": api.safe_unicode(address.get("city", "")),
            }])

        return {
            "mrn": mrn,
            "sex": sex,
            "birthdate": birthdate,
            "address": address,
            "gender": "",
            "firstname": api.safe_unicode(firstname),
            "middlename": api.safe_unicode(middlename),
            "lastname": api.safe_unicode(lastname),
            "portal_type": "Patient",
        }
