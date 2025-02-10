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

from AccessControl import ClassSecurityInfo
from bes.lims import messageFactory as _
from bes.lims.vocabularies import CONTAINER_TYPE_WIDGETS_VOCABULARY
from bika.lims import api
from plone.app.textfield import IRichTextValue
from plone.app.textfield.widget import RichTextFieldWidget
from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.supermodel import model
from Products.CMFCore import permissions
from senaite.core.api import measure as mapi
from senaite.core.interfaces import ISampleType
from senaite.core.schema import RichTextField
from zope import schema
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Invalid
from zope.interface import invariant
from zope.interface import provider


@provider(IFormFieldProvider)
class IExtendedSampleTypeBehavior(model.Schema):

    require_collector_or_sampler = schema.Bool(
        title=_(u"Collector/Sampler Required"),
        description=_(
            u"This field determines whether the sample requires "
            u"a 'Collector' or 'Sampler.'"
        ),
        default=False,
    )

    container_widget = schema.Choice(
        title=_(u"Widget for container selection"),
        vocabulary=CONTAINER_TYPE_WIDGETS_VOCABULARY,
        default="container",
        required=True,
    )

    directives.widget("insufficient_volume_text", RichTextFieldWidget)
    insufficient_volume_text = RichTextField(
        title=_(u"Auto-text for when there is not enough volume"),
        description=_(
            u"When there is not enough volume, the contents entered here "
            u"are automatically inserted in Results Interpretation after "
            u"Sample verification"
        ),
        required=False
    )

    maximum_volume = schema.TextLine(
        title=_(u"Maximum Volume"),
        description=_(
            u"The maximum sample volume required for analysis eg. '10 ml' or "
            u"'1 kg'."
        ),
        required=False,
    )

    @invariant
    def validate_maximum_volume(data):
        """Checks if the volume is valid
        """
        volume = data.maximum_volume
        if not volume:
            # not required
            return

        context = getattr(data, "__context__", None)
        if context and context.maximum_volume == volume:
            # nothing changed
            return

        if not mapi.is_volume(volume):
            raise Invalid(_("Not a valid volume"))


@implementer(IExtendedSampleTypeBehavior)
@adapter(ISampleType)
class ExtendedSampleType(object):

    security = ClassSecurityInfo()

    def __init__(self, context):
        self.context = context

    @security.protected(permissions.View)
    def getRequireCollectorOrSampler(self):
        accessor = self.context.accessor("require_collector_or_sampler")
        return accessor(self.context)

    @security.protected(permissions.ModifyPortalContent)
    def setRequireCollectorOrSampler(self, value):
        mutator = self.context.mutator("require_collector_or_sampler")
        mutator(self.context, value)

    require_collector_or_sampler = property(getRequireCollectorOrSampler,
                                            setRequireCollectorOrSampler)

    @security.protected(permissions.View)
    def getContainerWidget(self):
        accessor = self.context.accessor("container_widget")
        return api.to_utf8(accessor(self.context))

    @security.protected(permissions.ModifyPortalContent)
    def setContainerWidget(self, value):
        mutator = self.context.mutator("container_widget")
        mutator(self.context, api.safe_unicode(value))

    container_widget = property(getContainerWidget, setContainerWidget)

    @security.protected(permissions.View)
    def getInsufficientVolumeText(self):
        accessor = self.context.accessor("insufficient_volume_text")
        value = accessor(self.context)
        if IRichTextValue.providedBy(value):
            # Transforms the raw value to the output mimetype
            value = value.output_relative_to(self.context)
        # XX we don't do to_utf8 cause the RichTextWidgetConverter's
        # toWidgetValue expects a unicode, a RichTextValue or None. Otherwise,
        # the following traceback arises:
        #   ...
        #   Module plone.app.textfield.widget, line 112, in toWidgetValue
        # ValueError: Can not convert '<p>bla</p>' to an IRichTextValue
        return value

    @security.protected(permissions.ModifyPortalContent)
    def setInsufficientVolumeText(self, value):
        mutator = self.context.mutator("insufficient_volume_text")
        mutator(self.context, value)

    insufficient_volume_text = property(getInsufficientVolumeText,
                                        setInsufficientVolumeText)

    @security.protected(permissions.View)
    def getMaximumVolume(self):
        accessor = self.context.accessor("maximum_volume")
        value = accessor(self.context) or ""
        return api.to_utf8(value)

    @security.protected(permissions.ModifyPortalContent)
    def setMaximumVolume(self, value):
        mutator = self.context.mutator("maximum_volume")
        mutator(self.context, api.safe_unicode(value))

    maximum_volume = property(getMaximumVolume, setMaximumVolume)


def getRequireCollectorOrSampler(self):
    behavior = IExtendedSampleTypeBehavior(self)
    return behavior.getRequireCollectorOrSampler()


def setRequireCollectorOrSampler(self, value):
    behavior = IExtendedSampleTypeBehavior(self)
    behavior.setRequireCollectorOrSampler(value)


def getContainerWidget(self):
    behavior = IExtendedSampleTypeBehavior(self)
    return behavior.getContainerWidget()


def setContainerWidget(self, value):
    behavior = IExtendedSampleTypeBehavior(self)
    behavior.setContainerWidget(value)


def getInsufficientVolumeText(self):
    behavior = IExtendedSampleTypeBehavior(self)
    return behavior.getInsufficientVolumeText()


def setInsufficientVolumeText(self, value):
    behavior = IExtendedSampleTypeBehavior(self)
    behavior.setInsufficientVolumeText(value)


def getMaximumVolume(self):
    behavior = IExtendedSampleTypeBehavior(self)
    return behavior.getMaximumVolume()


def setMaximumVolume(self, value):
    behavior = IExtendedSampleTypeBehavior(self)
    behavior.setMaximumVolume(value)
