# -*- coding: utf-8 -*-

import transaction
from bika.lims import api
from bes.lims import logger
from bes.lims.scripts import setup_script_environment
from senaite.core.upgrade.utils import delete_object
from senaite.patient.catalog import PATIENT_CATALOG


def main(app):
    # Setup environment
    setup_script_environment(app, stream_out=False)

    query = {
        "portal_type": "Patient",
        "review_state": "inactive",
    }

    brains = api.search(query, PATIENT_CATALOG)
    total = len(brains)
    logger.info("Deleting %s inactive patients ..." % total)
    for brain in brains:
        try:
            patient = brain.getObject()
        except AttributeError:
            # the object associated to the brain was removed already
            continue

        # delete the patient
        logger.info("Deleting %r ..." % patient)
        delete_object(patient)

    # Commit transaction
    logger.info("Commit transaction ...")
    transaction.commit()
    logger.info("Deleting %s inactive patients [DONE]" % total)


if __name__ == "__main__":
    main(app)  # noqa: F821
