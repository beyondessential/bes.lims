# -*- coding: utf-8 -*-

from bes.lims import _
from bika.lims import api
from bika.lims.utils import get_link
from senaite.app.listing.interfaces import IListingView
from senaite.app.listing.interfaces import IListingViewAdapter
from senaite.app.listing.utils import add_column
from zope.component import adapter
from zope.interface import implementer


# Columns to add
ADD_COLUMNS = [
    ("TamanuID", {
        "title": _("Tamanu ID"),
        "sortable": False,
        "after": "getId",
    }),
]


@implementer(IListingViewAdapter)
@adapter(IListingView)
class SamplesListingAdapter(object):
    """Adapter for sample listings
    """

    # Priority order of this adapter over others
    priority_order = 9999

    def __init__(self, listing, context):
        self.listing = listing
        self.context = context

    def folder_item(self, obj, item, index):
        obj = api.get_object(obj)
        tid = obj.getTamanuID()
        if tid:
            item["TamanuID"] = tid
            el = "<span class='text-monospace'>%s</span>" % tid
            item["replace"]["TamanuID"] = el

    def before_render(self):
        # Additional columns
        rv_keys = map(lambda r: r["id"], self.listing.review_states)
        for column_id, column_values in ADD_COLUMNS:
            add_column(
                listing=self.listing,
                column_id=column_id,
                column_values=column_values,
                after=column_values.get("after", None),
                review_states=rv_keys)
