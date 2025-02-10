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

import copy

from plone.dexterity.browser import edit


class SampleTypeEditForm(edit.DefaultEditForm):
    """SampleType edit view
    """
    portal_type = "SampleType"

    def updateFieldsFromSchemata(self):
        """see plone.autoform.base.AutoFields
        """
        super(SampleTypeEditForm, self).updateFieldsFromSchemata()

        # Make the min volume field non-required
        # Schema fields are shared between instances by default, so we need to
        # create a copy of it
        min_vol = self.fields["min_volume"]
        min_vol_field = copy.copy(min_vol.field)
        min_vol_field.required = False
        min_vol.field = min_vol_field
