# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# Copyright 2024 Beyond Essential Systems Pty Ltd

from bes.lims import logger
from bes.lims import permissions
from senaite.core.setuphandlers import setup_core_catalogs
from senaite.core.setuphandlers import setup_other_catalogs
from senaite.core.catalog import ANALYSIS_CATALOG
from senaite.core.workflow import ANALYSIS_WORKFLOW
from senaite.core.api import workflow as wapi


CATALOGS = (
    # Add-on specific Catalogs (list of core's BaseCatalog objects)
)

INDEXES = [
    # Tuples of (catalog, index_name, index_attribute, index_type)
    (ANALYSIS_CATALOG, "department_uid", "", "FieldIndex"),
]

COLUMNS = [
    # Tuples of (catalog, column_name)
]

# Workflow updates
WORKFLOWS_TO_UPDATE = {
    ANALYSIS_WORKFLOW: {
        "states": {
            "assigned": {
                "transitions": ["set_out_of_stock"],
            },
            "unassigned": {
                "transitions": ["set_out_of_stock"],
            },
            "out_of_stock": {
                "title": "Out of Stock",
                "transitions": ["rollback"],
                "permissions_copy_from": "rejected",
            },
        },
        "transitions": {
            "set_out_of_stock": {
                "title": "Set Out of Stock",
                "new_state": "out_of_stock",
                "action": "Set Out of Stock",
                "after_script": "",
                "guard": {
                    "guard_permissions": permissions.TransitionSetOutOfStock,
                    "guard_roles": "",
                    "guard_expr":
                        "python:here.guard_handler('set_out_of_stock')",
                }
            },
            "rollback": {
                "title": "Rollback",
                "new_state": "",
                "action": "Rollback to previous status",
                "after_script": "",
                "guard": {
                    "guard_permissions": permissions.TransitionRollback,
                    "guard_roles": "",
                    "guard_expr": "python:here.guard_handler('rollback')",
                }
            },
        }
    },
}


def setup_handler(context):
    """Setup handler
    """

    if context.readDataFile("bes.lims.txt") is None:
        return

    logger.info("BES setup handler [BEGIN]")

    portal = context.getSite()

    # Setup Catalogs
    setup_catalogs(portal)

    # Setup workflows
    setup_workflows(portal)

    logger.info("BES setup handler [DONE]")


def setup_catalogs(portal):
    """Setup catalogs
    """
    logger.info("Setup Catalogs ...")

    setup_core_catalogs(portal, catalog_classes=CATALOGS)
    setup_other_catalogs(portal, indexes=INDEXES, columns=COLUMNS)

    logger.info("Setup Catalogs [DONE]")


def setup_workflows(portal):
    """Setup workflow changes (status, transitions, permissions, etc.)
    """
    logger.info("Setup workflows ...")
    for wf_id, settings in WORKFLOWS_TO_UPDATE.items():
        wapi.update_workflow(wf_id, **settings)
    logger.info("Setup workflows [DONE]")
