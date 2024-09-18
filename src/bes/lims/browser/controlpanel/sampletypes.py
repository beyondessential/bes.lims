# -*- coding: utf-8 -*-

from bes.lims import messageFactory as _
from bika.lims import api
from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from zope.component import adapter
from zope.interface import implementer


@adapter(IListingView)
@implementer(IListingViewAdapter)
class SampleTypesClientsListingAdapter(object):
    """Adapter for sample types listings
    """

    # Priority order of this adapter over others
    priority = 1000

    def __init__(self, listing, context):
        self.listing = listing
        self.context = context

    def before_render(self):
        self.listing.columns["MaximumVolume"] = {
            "title": _("Maximum Volume"),
            "toggle": True
        }

        for rv in self.listing.review_states:
            rv["columns"] = self.listing.columns.keys()

    def folder_item(self, obj, item, index):
        obj = api.get_object(obj)
        maximum_vol = obj.getMaximumVolume()
        item["MaximumVolume"] = maximum_vol
        return item
