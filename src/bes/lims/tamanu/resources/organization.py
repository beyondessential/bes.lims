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


class Organization(TamanuResource):
    """Object that represents an Organization resource from Tamanu
    """

    def to_object_info(self):
        """Returns a dict representation of the Organization resource, suitable
        for the creation and edition of SENAITE's Organisation objects like
        Client, Supplier, Manufacturer, etc.
        """
        name = self.get("name")
        return {
            "Name": name,
            "title": name,
            "TaxNumber": "",
            "Phone": "",
            "Fax": "",
            "EmailAddress": "",
            "PhysicalAddress": {},
            "PostalAddress": {},
            "BillingAddress": {},
            "AccountType": "",
            "AccountName": "",
            "BankName": "",
            "BankBranch": "",
        }
