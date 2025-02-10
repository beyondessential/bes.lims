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

from bes.lims import messageFactory as _
from senaite.core.schema.vocabulary import to_simple_vocabulary
from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory

CONTAINER_TYPE_WIDGETS_VOCABULARY = "bes.lims.vocabularies.container_type_widgets"  # noqa

CONTAINER_TYPE_WIDGETS = (
    ("container", _("Generic search control")),
    ("bottles", _("BACTEC bottles control")),
)


@implementer(IVocabularyFactory)
class ContainerTypeWidgetsVocabularyFactory(object):

    def __call__(self, context):
        return to_simple_vocabulary(CONTAINER_TYPE_WIDGETS)


# Factory
ContainerTypeWidgetsVocabularyFactory = ContainerTypeWidgetsVocabularyFactory()
