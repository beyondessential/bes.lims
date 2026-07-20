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

from Products.Archetypes.Widget import StringWidget
from Products.CMFCore.permissions import View
from archetypes.schemaextender.interfaces import IBrowserLayerAwareExtender
from archetypes.schemaextender.interfaces import ISchemaExtender
from archetypes.schemaextender.interfaces import ISchemaModifier
from bes.lims import messageFactory as _
from bes.lims.extender.field import ExtSiteField
from bes.lims.extender.field import ExtStringField
from bes.lims.interfaces import IBESLimsLayer
from bika.lims.interfaces import IAnalysisRequest
from senaite.core.browser.widgets import QuerySelectWidget
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.permissions import FieldEditClientSampleID
from senaite.core.permissions import FieldEditSampler
from senaite.core.permissions import FieldEditSamplePoint
from zope.component import adapter
from zope.interface import implementer


# A list with the names of the fields to be disabled. SamplePoint is replaced
# by the Site field below, that additionally allows a custom text value
DISABLED_FIELDS = [
    "SamplePoint",
]


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
    ExtStringField(
        "TamanuID",
        default="",
        mode="rw",
        read_permission=View,
        write_permission=FieldEditClientSampleID,
        widget=StringWidget(
            label=_("Tamanu ID"),
            description=_(
                "The identifier of the corresponding ServiceRequest in Tamanu"
            ),
            # Display Tamanu ID in readonly mode only
            visible={
                "add": "invisible",
                "edit": "disabled",
                "secondary": "disabled",
            }
        )
    ),
    ExtSiteField(
        "Site",
        mode="rw",
        read_permission=View,
        write_permission=FieldEditSamplePoint,
        widget=QuerySelectWidget(
            label=_("Site"),
            description=_("Location where the sample was taken"),
            render_own_label=True,
            catalog=SETUP_CATALOG,
            search_index="Title",
            value_key="uid",
            search_wildcard=True,
            multi_valued=False,
            allow_user_value=True,
            i18n_domain="bes.lims",
            visible={
                "add": "edit",
                "secondary": "disabled",
            },
            query={
                "portal_type": "SamplePoint",
                "is_active": True,
                "sort_on": "sortable_title",
                "sort_order": "ascending"
            },
            columns=[
                {
                    "name": "Title",
                    "align": "left",
                    "label": _(u"Title"),
                }, {
                    "name": "Description",
                    "align": "left",
                    "label": _(u"Description"),
                },
            ],
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


def disable_field(schema, field_id):
    """Hides and makes the schema field for the given id as non required
    """
    schema[field_id].required = False
    schema[field_id].widget.visible = False


@adapter(IAnalysisRequest)
@implementer(ISchemaModifier, IBrowserLayerAwareExtender)
class AnalysisRequestSchemaModifier(object):
    """Modifies existing fields of the Sample (aka AnalysisRequest)
    """
    layer = IBESLimsLayer

    def __init__(self, context):
        self.context = context

    def fiddle(self, schema):
        for field_id in DISABLED_FIELDS:
            disable_field(schema, field_id)
        return schema


def getSite(self):
    """Returns the Site assigned to the sample, if any
    """
    return self.getField("Site").get(self)


def setSite(self, value):
    """Assigns the site to the sample
    """
    self.getField("Site").set(self, value)


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


def getTamanuID(self):
    """Returns the Tamanu ID of the sample/specimen, if any
    """
    return self.getField("TamanuID").get(self)


def setTamanuID(self, value):
    """Sets the Tamanu ID of the sample/specimen
    """
    self.getField("TamanuID").set(self, value)

