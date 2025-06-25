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

SALUTATIONS = ("dr", "mr", "ms", "mx")


class HumanName(dict):
    """Object that represents an HL7 HumanName datatype
    https://www.hl7.org/fhir/datatypes.html#humanname
    """

    def get_name_info(self):
        """Returns a dict with the name parts
        """
        info = {
            "Salutation": "",
            "Firstname": "",
            "Middleinitial": "",
            "Middlename": "",
            "Surname": "",
        }

        family = self.get("familyName")
        given = self.get("given")
        if family and given:
            info.update({
                "Salutation": self.get("prefix"),
                "Firstname": given[0],
                "Surname": family,
                "Middlename": " ".join(given[1:]),
            })
            return info

        # Rely on the 'text' entry
        fullname = self.get("text")
        parts = filter(None, fullname.split(" "))
        if not parts:
            return info

        if len(parts) == 1:
            info["Firstname"] = parts[0]
            return info

        if parts[0].strip(".").lower() in SALUTATIONS:
            info["Salutation"] = parts[0]
            parts = parts[1:]

        info["Firstname"] = parts[0]
        info["Surname"] = " ".join(parts[1:])
        return info
