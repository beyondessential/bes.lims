# -*- coding: utf-8 -*-

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
