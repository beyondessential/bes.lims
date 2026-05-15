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

from bika.lims import api
from bika.lims.adapters.dynamicresultsrange import marker


def get_results_range(self):
    """Return dynamic range values and preserve textual `rangecomment`."""
    if self.dynamicspec is None:
        return {}

    # A matching Analysis Keyword is mandatory for any further matches
    keyword = self.analysis.getKeyword()
    by_keyword = self.dynamicspec.get_by_keyword()

    # Get all specs (rows) from the Excel with the same Keyword
    specs = by_keyword.get(keyword)
    if not specs:
        return {}

    # Filter those with a match
    specs = filter(self.match, specs)
    if not specs:
        return {}

    # Sort them and pick the first match, that is less generic
    spec = sorted(specs, cmp=self.cmp_specs)[0]

    # at this point we have a match, update the results range dict
    rr = {}
    for key in self.range_keys:
        value = spec.get(key, marker)
        # skip if the range key is not set in the Excel
        if value is marker:
            continue
        # skip if the value is not floatable
        if not api.is_floatable(value):
            continue
        rr[key] = value

    # Support both "rangecomment" and "Range comment" XLSX headers
    comment = spec.get("rangecomment") or spec.get("Range comment")
    if comment and api.is_string(comment):
        rr["rangecomment"] = comment.strip()


    # return the updated result range
    return rr
