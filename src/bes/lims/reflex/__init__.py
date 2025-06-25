# -*- coding: utf-8 -*-

from zope.component import queryAdapter
from zope.interface import Interface
from zope.interface import implements


class IReflexTesting(Interface):
    """Marker interface for Reflex Testing Adapters
    """

    def __call__(self):
        """Executes the reflex testing for the analysis
        """


class ReflexTestingBaseAdapter(object):
    """Base Reflex Testing Adapter
    """
    implements(IReflexTesting)

    def __init__(self, analysis):
        self.analysis = analysis


def get_reflex_testing_adapter(analysis, action):
    """Returns a reflex testing adapter for this analysis, if any
    """
    keyword = analysis.getKeyword()

    # Replace special characters from the keyword
    keyword = keyword.replace("-", "")
    keyword = keyword.lower()

    # Run CINTER's reflex testing when keyword *starts* with CINTER
    # https://github.com/beyondessential/pnghealth.lims/issues/127
    if keyword.startswith("cinter"):
        keyword = "cinter"

    name = "bes.lims.reflex.{}.{}".format(keyword, action)
    return queryAdapter(analysis, IReflexTesting, name=name)
