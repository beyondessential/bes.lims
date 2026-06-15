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
from archetypes.schemaextender.interfaces import ISchemaModifier
from bes.lims import messageFactory as _
from bes.lims.extender.field import ExtBooleanField
from bes.lims.interfaces import IBESLimsLayer
from bika.lims import senaiteMessageFactory as _c
from bika.lims.interfaces import IBaseAnalysis
from Products.Archetypes import DisplayList
from Products.Archetypes.Widget import BooleanWidget
from zope.component import adapter
from zope.interface import implementer


NEW_FIELDS = [
    ExtBooleanField(
        "ExcludeFromIntegration",
        schemata="Analysis",
        default=False,
        widget=BooleanWidget(
            label=_("Exclude from integration"),
            description=_(
                "If enabled, the result of this analysis will not be sent to "
                "integrated systems (e.g. Tamanu). The integrated system will "
                "receive 'Refer to PDF report' in place of the actual result."
            ),
        )
    ),
]


UPDATED_FIELDS = [
    ("ResultOptions", {
        "subfields": ("ResultValue", "ResultText", "AllowManualEntry", "Flag"),
        "subfield_labels": {
            "ResultValue": _c("Result Value"),
            "ResultText": _c("Display Value"),
            "AllowManualEntry": _c("Allow Manual Entry"),
            "Flag": _("Flag"),
        },
        "subfield_types": {
            "AllowManualEntry": "boolean",
            "Flag": "selection",
        },
        "subfield_sizes": {
            "AllowManualEntry": 8,
            "Flag": 1,
        },
        "subfield_vocabularies": {
            "Flag": DisplayList((
                ("", ""),
                ("negative", _("Negative")),
                ("positive", _("Positive")),
            )),
        },
    }),
]


def update_field(schema, field_id, field_info):
    """Updates the schema field with the field_info provided
    """
    field = schema[field_id]
    for prop_id, prop_value in field_info.items():
        if not hasattr(field, prop_id):
            continue
        setattr(field, prop_id, prop_value)


@adapter(IBaseAnalysis)
@implementer(ISchemaExtender, IBrowserLayerAwareExtender)
class BaseAnalysisSchemaExtender(object):
    layer = IBESLimsLayer

    def __init__(self, context):
        self.context = context

    def getFields(self):  # noqa CamelCase
        return NEW_FIELDS


@adapter(IBaseAnalysis)
@implementer(ISchemaModifier, IBrowserLayerAwareExtender)
class BaseAnalysisSchemaModifier(object):
    layer = IBESLimsLayer

    def __init__(self, context):
        self.context = context

    def fiddle(self, schema):
        for field_name, field_info in UPDATED_FIELDS:
            update_field(schema, field_name, field_info)
        return schema


def getExcludeFromIntegration(self):
    """Returns whether this analysis result should be excluded from
    integrated systems (e.g. Tamanu)
    """
    return self.getField("ExcludeFromIntegration").get(self)


def setExcludeFromIntegration(self, value):
    """Sets whether this analysis result should be excluded from
    integrated systems (e.g. Tamanu)
    """
    self.getField("ExcludeFromIntegration").set(self, value)
