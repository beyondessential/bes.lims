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

from DateTime import DateTime
from bes.lims.reflex import get_reflex_testing_adapter
from bes.lims.utils import get_previous_status
from bika.lims import api
from bika.lims.interfaces import ISubmitted
from bika.lims.interfaces import IVerified
from bika.lims.workflow import doActionFor
from senaite.core.workflow import ANALYSIS_WORKFLOW
from zope.interface import alsoProvides


def after_submit(analysis):
    """Event fired when an analysis result gets submitted
    """
    # Handle reflex testing if necessary
    adapter = get_reflex_testing_adapter(analysis, "submit")
    if adapter:
        adapter()


def after_verify(analysis):
    """Event fired when an analysis result gets submitted
    """
    # Handle reflex testing if necessary
    adapter = get_reflex_testing_adapter(analysis, "verify")
    if adapter:
        adapter()


def after_set_out_of_stock(analysis):
    """Event fired when an analysis is transitioned to out-of-stock
    """
    # Mark the analysis with ISubmitted so samples with only one analysis in
    # out-of-stock can also be pre-published
    alsoProvides(analysis, ISubmitted)

    # Mark the analysis with IVerified so samples with only one analysis in
    # out-of-stock can also be published
    alsoProvides(analysis, IVerified)

    # Try to submit the sample
    sample = analysis.getRequest()
    doActionFor(sample, "submit")


def after_rollback(analysis):
    """Event fired when the rollback transition takes place. Transitions the
    analysis back to the previous status
    """
    portal_workflow = api.get_tool("portal_workflow")
    workflow = portal_workflow.getWorkflowById(ANALYSIS_WORKFLOW)
    prev = get_previous_status(analysis)
    wf_state = {
        "action": "rollback",
        "actor": api.get_current_user().id,
        "comments": "Rollback",
        "review_state": prev,
        "time": DateTime()
    }
    portal_workflow.setStatusOf(ANALYSIS_WORKFLOW, analysis, wf_state)
    workflow.updateRoleMappingsFor(analysis)
    analysis.reindexObject()
