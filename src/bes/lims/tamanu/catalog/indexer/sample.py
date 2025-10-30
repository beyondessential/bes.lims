# -*- coding: utf-8 -*-

from bes.lims.interfaces import IBESLimsLayer
from bika.lims.interfaces import IAnalysisRequest
from bika.lims.interfaces import IListingSearchableTextProvider
from senaite.core.interfaces import ISampleCatalog
from zope.component import adapter
from zope.interface import implementer


@adapter(IAnalysisRequest, IBESLimsLayer, ISampleCatalog)
@implementer(IListingSearchableTextProvider)
class ListingSearchableTextProvider(object):
    """Adapter that extends existing listing_searchable_text index with
    additional tokens related with Tamanu EHR
    """
    def __init__(self, context, request, catalog):
        self.context = context
        self.request = request
        self.catalog = catalog

    def __call__(self):
        tokens = [
            self.context.getTamanuID(),
        ]
        return filter(None, tokens)
