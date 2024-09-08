# -*- coding: utf-8 -*-

from bes.lims.utils import get_previous_status
from bika.lims import api
from bika.lims.interfaces import ISubmitted
from bika.lims.interfaces import IVerified
from bika.lims.workflow import doActionFor
from DateTime import DateTime
from senaite.core.workflow import ANALYSIS_WORKFLOW
from zope.interface import alsoProvides


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
