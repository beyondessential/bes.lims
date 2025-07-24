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
from bes.lims.extender.field import ExtStringField
from bes.lims.interfaces import IBESLimsLayer
from bika.lims.interfaces import IAnalysisRequest
from Products.Archetypes.Widget import StringWidget
from Products.CMFCore.permissions import View
from senaite.core.permissions import FieldEditSampler
from zope.component import adapter
from zope.interface import implementer


# Additional fields for Sample (aka AnalysisRequest)
NEW_FIELDS = [
    ExtStringField(
        "Collector",
        default="",
        mode="rw",
        read_permission=View,
        write_permission=FieldEditSampler,
        widget=StringWidget(
            render_own_label=True,
            size=20,
            label=_("Collector"),
            description=_("The practitioner who collected the sample"),
            visible={
                "add": "edit",
            }
        )
    ),

]


@adapter(IAnalysisRequest)
@implementer(ISchemaExtender, IBrowserLayerAwareExtender)
class AnalysisRequestSchemaExtender(object):
    """Extends the Sample (aka AnalysisRequest) with additional fields
    """
    layer = IBESLimsLayer

    def __init__(self, context):
        self.context = context

    def getFields(self):  # noqa CamelCase
        return NEW_FIELDS


def getCollector(self):
    """Returns the collector of the sample/specimen, if any
    """
    return self.getField("Collector").get(self)


def setCollector(self, value):
    """Returns the collector of the sample/specimen, if any
    """
    self.getField("Collector").set(self, value)
    # Keep sampler field in-sync
    self.getField("Sampler").set(self, value)
