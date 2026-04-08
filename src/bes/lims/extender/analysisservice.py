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
# Copyright 2026 by it's authors.
# Some rights reserved, see README and LICENSE.

from archetypes.schemaextender.interfaces import IBrowserLayerAwareExtender
from archetypes.schemaextender.interfaces import ISchemaModifier
from bes.lims.interfaces import IBESLimsLayer
from bes.lims.config import RESULT_TYPES
from bes.lims.extender import update_field
from bika.lims.interfaces import IAnalysisService
from zope.component import adapter
from zope.interface import implementer


UPDATED_FIELDS = [
    ("InterimFields", {
        "subfield_vocabularies": {
            "result_type": RESULT_TYPES,
        },
    }),
]


@adapter(IAnalysisService)
@implementer(ISchemaModifier, IBrowserLayerAwareExtender)
class AnalysisServiceInterimFieldsSchemaModifier(object):
    """Updates InterimFields schema for AnalysisService.
    """

    layer = IBESLimsLayer

    def __init__(self, context):
        self.context = context

    def fiddle(self, schema):
        # Update some fields (title, description, etc.)
        map(lambda f: update_field(schema, f[0], f[1]), UPDATED_FIELDS)
        return schema
