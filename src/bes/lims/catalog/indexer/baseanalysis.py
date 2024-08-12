# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# Copyright 2024 Beyond Essential Systems Pty Ltd

from bika.lims.interfaces import IBaseAnalysis
from plone.indexer import indexer
from senaite.core.interfaces import IAnalysisCatalog


@indexer(IBaseAnalysis, IAnalysisCatalog)
def department_uid(instance):
    """Returns the department uid assigned to this instance or empty
    """
    return instance.getRawDepartment() or ""
