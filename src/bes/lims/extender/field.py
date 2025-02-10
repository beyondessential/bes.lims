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

from archetypes.schemaextender.field import ExtensionField as ATExtensionField
from bika.lims.browser.fields import UIDReferenceField
from plone.app.blob.field import ImageField as BlobImageField
from Products.Archetypes.Field import FixedPointField
from Products.Archetypes.Field import StringField
from Products.Archetypes.Field import BooleanField
from Products.Archetypes.Field import IntegerField
from Products.Archetypes.Field import TextField
from senaite.core.browser.fields.datetime import DateTimeField
from senaite.core.browser.fields.records import RecordsField


class ExtensionField(ATExtensionField):
    """Mix-in class to make Archetypes fields not depend on generated accessors
    and mutators, and use AnnotationStorage by default
    """

    def __init__(self, *args, **kwargs):
        super(ExtensionField, self).__init__(*args, **kwargs)


class ExtBlobImageField(ExtensionField, BlobImageField):
    """Field extender of plone.app.blob's ImageField
    """


class ExtBooleanField(ExtensionField, BooleanField):
    """Field extender of BooleanField
    """


class ExtDateTimeField(ExtensionField, DateTimeField):
    """Field extender of DateTimeField
    """


class ExtFixedPointField(ExtensionField, FixedPointField):
    """Field extender of FixedPointField
    """


class ExtIntegerField(ExtensionField, IntegerField):
    """Field extender of IntegerField
    """


class ExtRecordsField(ExtensionField, RecordsField):
    """Field Extender of RecordsField
    """


class ExtStringField(ExtensionField, StringField):
    """Field extender of StringField
    """


class ExtTextField(ExtensionField, TextField):
    """Field extender of TextField
    """


class ExtUIDReferenceField(ExtensionField, UIDReferenceField):
    """Field Extender of core's UIDReferenceField for AT types
    """
