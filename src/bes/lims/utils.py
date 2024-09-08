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


def get_previous_status(instance, before=None, default=None):
    """Returns the previous state for the given instance and status from
    review history. If before is None, returns the state of the sample before
    its current status.
    """
    if not before:
        before = api.get_review_status(instance)

    # Get the review history, most recent actions first
    found = False
    history = api.get_review_history(instance)
    for item in history:
        status = item.get("review_state")
        if status == before:
            found = True
            continue
        if found:
            return status
    return default
