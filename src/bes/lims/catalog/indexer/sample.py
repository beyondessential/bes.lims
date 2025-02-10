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
from bika.lims.interfaces import IAnalysisRequest
from plone.indexer import indexer
from senaite.core.interfaces import ISampleCatalog

DETACHED_STATES = ["cancelled", "rejected", "retracted"]


@indexer(IAnalysisRequest, ISampleCatalog)
def department_uid(instance):
    """Returns the department uids assigned to the analyses that belong to this
    sample (instance). If no department assigned, it returns a list with an
    empty value to allow searches for `MissingValue`.
    """
    uids = set()
    for obj in instance.objectValues(spec="Analysis"):
        if api.get_review_status(obj) in DETACHED_STATES:
            continue
        uid = obj.getRawDepartment()
        if not api.is_uid(uid):
            continue
        uids.add(uid)

    return list(uids) if uids else [""]
