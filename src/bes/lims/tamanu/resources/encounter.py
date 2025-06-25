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


class Encounter(TamanuResource):
    """Object that represents an Encounter resource from Tamanu
    """

    def getLocation(self):
        """Returns the Location resource assigned to this Encounter, if any
        """
        return self.get("subject")

    def getServiceProvider(self):
        """Returns the ServiceProvider resource assigned to this Encounter
        """
        return self.get("serviceProvider")
