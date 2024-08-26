# -*- coding: utf-8 -*-

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
