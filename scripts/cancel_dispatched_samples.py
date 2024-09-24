# -*- coding: utf-8 -*-

import transaction
from bika.lims import api
from DateTime import DateTime
from bes.lims import logger
from bes.lims.scripts import setup_script_environment
from senaite.core.catalog import SAMPLE_CATALOG
from senaite.core.workflow import SAMPLE_WORKFLOW


def main(app):
    # Setup environment
    setup_script_environment(app)

    query = {
        "portal_type": "AnalysisRequest",
        "review_state": "dispatched"
    }

    portal_workflow = api.get_tool("portal_workflow")
    workflow = portal_workflow.getWorkflowById(SAMPLE_WORKFLOW)

    brains = api.search(query, SAMPLE_CATALOG)
    total = len(brains)
    for num, brain in enumerate(brains):
        if num > 0 and num % 100 == 0:
            logger.info("Canceling dispatched: {}/{}".format(num, total))

        obj = api.get_object(brain)
        logger.info("Canceling dispatched sample: %r" % obj)

        wf_state = {
            "action": "cancel",
            "actor": api.get_current_user().id,
            "comments": "Auto-cancel dispatched samples. See #174",
            "review_state": "cancelled",
            "time": DateTime()
        }
        portal_workflow.setStatusOf(SAMPLE_WORKFLOW, obj, wf_state)
        workflow.updateRoleMappingsFor(obj)
        obj.reindexObject()

        # Flush the object from memory
        obj._p_deactivate()

    # Commit transaction
    logger.info("Commit transaction ...")
    transaction.commit()
    logger.info("Commit transaction [DONE]")


if __name__ == "__main__":
    main(app)  # noqa: F821
