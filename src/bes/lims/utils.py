# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# Copyright 2024 Beyond Essential Systems Pty Ltd

from bes.lims.config import ANALYSIS_REPORTABLE_STATUSES
from bika.lims import api
from bika.lims.interfaces import IInternalUse
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.utils import is_ast_analysis


def is_reportable(analysis):
    """Returns whether the analysis has to be displayed in results reports
    """
    # do not report hidden analyses
    if analysis.getHidden():
        return False

    # do not report analyses for internal use
    if IInternalUse.providedBy(analysis):
        return False

    # do not report ast analyses, but resistance category only
    if is_ast_analysis(analysis):
        if analysis.getKeyword() != RESISTANCE_KEY:
            return False

    status = api.get_review_status(analysis)
    return status in ANALYSIS_REPORTABLE_STATUSES
