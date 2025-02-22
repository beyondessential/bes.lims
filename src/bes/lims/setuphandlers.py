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

from bes.lims import logger
from bes.lims import permissions
from bes.lims import PRODUCT_NAME
from bika.lims import api
from bika.lims.api import security as sapi
from plone import api as ploneapi
from senaite.core import permissions as core_permissions
from senaite.core.api import workflow as wapi
from senaite.core.catalog import ANALYSIS_CATALOG
from senaite.core.catalog import SAMPLE_CATALOG
from senaite.core.setuphandlers import setup_core_catalogs
from senaite.core.setuphandlers import setup_other_catalogs
from senaite.core.workflow import ANALYSIS_WORKFLOW
from senaite.core.workflow import SAMPLE_WORKFLOW

CATALOGS = (
    # Add-on specific Catalogs (list of core's BaseCatalog objects)
)

INDEXES = [
    # Tuples of (catalog, index_name, index_attribute, index_type)
    (ANALYSIS_CATALOG, "department_uid", "", "FieldIndex"),
    (SAMPLE_CATALOG, "department_uid", "", "KeywordIndex"),
]

COLUMNS = [
    # Tuples of (catalog, column_name)
]

# Tuples of (portal_type, list of behaviors)
BEHAVIORS = [
    ("SampleType", [
        "bes.lims.behaviors.sampletype.IExtendedSampleTypeBehavior",
    ]),
]


# List of tuples of (role, path, [(permissions, acquire), ...])
# When path is empty/None, the permissions are applied to portal object
# This allows to programmatically add roles for a given permission without
# having to overwrite the existing permission assignment in our rolemap.xml
ROLES = [
    ("Scientist", "", [
        # Allow Scientist role to add analyses by default
        (core_permissions.AddAnalysis, 0),
    ]),
    ("Rejector", "", [
        # Allow Rejector role to reject analyses by default
        (core_permissions.TransitionRejectAnalysis, 0),
    ]),
]

# List of tuples of (id, title, roles)
GROUPS = [
    ("Scientists", "Scientists", [
        "Member", "Analyst", "Scientist",
    ]),
    ("Rejectors", "Rejectors", [
        "Member", "Analyst", "Rejector",
    ])
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
    SAMPLE_WORKFLOW: {
        "states": {
            "to_be_verified": {
                "permissions": {
                    # allow Scientist role to add analyses in to_be_verified
                    core_permissions.AddAnalysis: ["Scientist", ]
                }
            }
        }
    }
}


def setup_handler(context):
    """Setup handler
    """

    if context.readDataFile("bes.lims.txt") is None:
        return

    logger.info("BES setup handler [BEGIN]")

    portal = context.getSite()
    setup = portal.portal_setup  # noqa

    # Run required import steps
    profile = "profile-{0}:default".format(PRODUCT_NAME)
    setup.runImportStepFromProfile(profile, "actions")
    setup.runImportStepFromProfile(profile, "rolemap")
    setup.runImportStepFromProfile(profile, "skins")

    # Setup roles
    setup_roles(portal)

    # Setup groups
    setup_groups(portal)

    # Setup Catalogs
    setup_catalogs(portal)

    # Add behaviors
    setup_behaviors(portal)

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


def setup_behaviors(portal):
    """Assigns additional behaviors to existing content types
    """
    logger.info("Setup Behaviors ...")
    pt = api.get_tool("portal_types")
    for portal_type, behavior_ids in BEHAVIORS:
        fti = pt.get(portal_type)
        if not hasattr(fti, "behaviors"):
            # Skip, type is not registered yet probably (AT2DX migration)
            logger.warn("Behaviors is missing: {} [SKIP]".format(portal_type))
            continue
        fti_behaviors = fti.behaviors
        additional = filter(lambda b: b not in fti_behaviors, behavior_ids)
        if additional:
            fti_behaviors = list(fti_behaviors)
            fti_behaviors.extend(additional)
            fti.behaviors = tuple(fti_behaviors)

    logger.info("Setup Behaviors [DONE]")


def setup_workflows(portal):
    """Setup workflow changes (status, transitions, permissions, etc.)
    """
    logger.info("Setup workflows ...")
    for wf_id, settings in WORKFLOWS_TO_UPDATE.items():
        wapi.update_workflow(wf_id, **settings)
    logger.info("Setup workflows [DONE]")


def setup_roles(portal):
    """Setup roles
    """
    logger.info("Setup roles ...")
    for role, path, perms in ROLES:
        folder_path = path or api.get_path(portal)
        folder = api.get_object_by_path(folder_path)
        for permission, acq in perms:
            logger.info("{} {} {} (acquire={})".format(role, folder_path,
                                                       permission, acq))
            sapi.grant_permission_for(folder, permission, role, acquire=acq)


def setup_groups(portal):
    """Setup roles and groups
    """
    logger.info("Setup groups ...")
    portal_groups = api.get_tool("portal_groups")
    for group_id, title, roles in GROUPS:

        # create the group and grant the roles
        if group_id not in portal_groups.listGroupIds():
            logger.info("Adding group {} ({}): {}".format(
                title, group_id, ", ".join(roles)))
            portal_groups.addGroup(group_id, title=title, roles=roles)

        # grant the roles to the existing group
        else:
            ploneapi.group.grant_roles(groupname=group_id, roles=roles)
            logger.info("Granting roles for group {} ({}): {}".format(
                title, group_id, ", ".join(roles)))

    logger.info("Setup groups [DONE]")
