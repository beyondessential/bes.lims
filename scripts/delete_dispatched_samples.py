# -*- coding: utf-8 -*-

import transaction
from bika.lims import api
from bes.lims import logger
from bes.lims.scripts import setup_script_environment
from senaite.core.catalog import SAMPLE_CATALOG
from senaite.core.upgrade.utils import delete_object


def assigned_to_worksheets(sample):
    """Returns a list with the worksheets this sample is assigned to
    """
    brains = sample.getAnalyses()
    for brain in brains:
        analysis = api.get_object(brain)
        if analysis.getWorksheetUID():
            return True
    return False


def main(app):
    # Setup environment
    setup_script_environment(app, stream_out=False)

    query = {
        "portal_type": "AnalysisRequest",
        "review_state": "dispatched",
    }

    brains = api.search(query, SAMPLE_CATALOG)
    total = len(brains)
    logger.info("Deleting %s dispatched samples ..." % total)
    for brain in brains:
        try:
            sample = brain.getObject()
        except AttributeError:
            # the object associated to the brain was removed already
            continue

        # is assigned to a worksheet?
        if assigned_to_worksheets(sample):
            sid = api.get_id(sample)
            logger.warn("[SKIP] Sample %s is assigned to a Worksheet" % sid)
            sample._p_deactivate()
            continue

        # delete the sample
        logger.info("Deleting %r ..." % sample)
        delete_object(sample)

    # Commit transaction
    logger.info("Commit transaction ...")
    transaction.commit()
    logger.info("Deleting %s dispatched samples [DONE]" % total)


if __name__ == "__main__":
    main(app)  # noqa: F821
