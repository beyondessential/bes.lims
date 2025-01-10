# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# Copyright 2024-2025 Beyond Essential Systems Pty Ltd

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
