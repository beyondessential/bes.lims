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

from archetypes.schemaextender.interfaces import IBrowserLayerAwareExtender
from archetypes.schemaextender.interfaces import ISchemaExtender
from bes.lims import messageFactory as _
from bes.lims.extender.field import ExtBlobImageField
from bes.lims.interfaces import IBESLimsLayer
from bika.lims.interfaces import IBikaSetup
from Products.Archetypes.Widget import ImageWidget
from zope.component import adapter
from zope.interface import implementer

# New fields to be added to this type
NEW_FIELDS = [

    ExtBlobImageField(
        "ReportLogo",
        schemata="Results Reports",
        widget=ImageWidget(
            label=_("Report Logo"),
            description=_(
                "Logo to display in the header of results reports"
            )
        ),
    ),

]


@adapter(IBikaSetup)
@implementer(ISchemaExtender, IBrowserLayerAwareExtender)
class SetupSchemaExtender(object):
    """Extends Setup content type with additional fields
    """
    layer = IBESLimsLayer

    def __init__(self, context):
        self.context = context

    def getFields(self):
        return NEW_FIELDS


def getReportLogo(self):
    """Returns the logo to display in the results report header
    """
    return self.getField("ReportLogo").get(self)


def setReportLogo(self, value):
    """Sets the logo to display in the results report header
    """
    return self.setField("ReportLogo").set(self, value)
