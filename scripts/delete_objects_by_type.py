# -*- coding: utf-8 -*-

import transaction
from bika.lims import api
from bes.lims import logger
from bes.lims.scripts import setup_script_environment
from bes.lims.scripts.utils import clear_and_rebuild
from senaite.core.interfaces import INumberGenerator
from senaite.core.upgrade.utils import delete_object
from zope.component import getUtility

TYPES_TO_DELETE = [
    "Worksheet",
    "ARReport",
    "Attachment",
    "AnalysisRequest",
    "Batch",
    "Report",
    "Patient",
]

CATALOGS_TO_CLEAR_AND_REBUILD = [
    "senaite_catalog",
    "senaite_catalog_analysis",
    "senaite_catalog_patient",
    "senaite_catalog_report",
    "senaite_catalog_sample",
    "senaite_catalog_setup",
    "senaite_catalog_worksheet",
    "portal_catalog",
    "uid_catalog",
    "reference_catalog"
]


def delete_objects():
    logger.info("Deleting objects by type ...")
    deleted = 0
    portal = api.get_portal()
    for portal_type in TYPES_TO_DELETE:

        # Delete objects
        deleted += delete_from(portal, portal_type)

    logger.info("Success: {} objects deleted".format(deleted))
    logger.info("Deleting objects by type [DONE]")
    return deleted


def reset_idserver():
    logger.info("Reset ID Server for deleted types ...")
    for portal_type in TYPES_TO_DELETE:
        pt_key = "{}-".format(portal_type.lower())
        number_generator = getUtility(INumberGenerator)
        ng_storage = number_generator.storage
        keys = ng_storage.keys()
        for key in keys:
            if key.startswith(pt_key):
                logger.info("Deleting ng {}".format(key))
                del ng_storage[key]
    logger.info("Reset ID Server for deleted types [DONE]")


def delete_from(folder, portal_type):
    deleted = 0
    for obj in folder.objectValues():
        if not api.is_object(obj):
            continue

        if api.get_portal_type(obj) == portal_type:
            path = api.get_path(obj)
            logger.info("Deleting {}".format(path))
            delete_object(obj)
            deleted += 1
            continue

        deleted += delete_from(obj, portal_type)
    return deleted


def main(app):
    # Setup environment
    setup_script_environment(app)

    # Delete objects
    delete_objects()

    # Reset ID Server
    reset_idserver()

    # Clear and rebuild catalogs
    clear_and_rebuild(CATALOGS_TO_CLEAR_AND_REBUILD)

    # Commit transaction
    logger.info("Commit transaction ...")
    transaction.commit()
    logger.info("Commit transaction [DONE]")


if __name__ == "__main__":
    main(app)  # noqa: F821
