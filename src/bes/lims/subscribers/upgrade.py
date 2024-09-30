# -*- coding: utf-8 -*-

from bes.lims import logger
from bes.lims import PRODUCT_NAME
from bes.lims.setuphandlers import setup_behaviors
from bes.lims.setuphandlers import setup_catalogs
from bes.lims.setuphandlers import setup_groups
from bes.lims.setuphandlers import setup_workflows
from bika.lims.api import get_portal


def afterUpgradeStepHandler(event):  # noqa CamelCase
    """Event handler executed after running an upgrade step of senaite.core
    """

    logger.info("Run {}.afterUpgradeStepHandler ...".format(PRODUCT_NAME))
    portal = get_portal()
    setup = portal.portal_setup  # noqa

    profile = "profile-{0}:default".format(PRODUCT_NAME)
    setup.runImportStepFromProfile(profile, "actions")
    setup.runImportStepFromProfile(profile, "rolemap")

    # Setup groups
    setup_groups(portal)

    # Setup catalogs
    setup_catalogs(portal)

    # Add behaviors
    setup_behaviors(portal)

    # Setup workflows
    setup_workflows(portal)

    logger.info("Run {}.afterUpgradeStepHandler [DONE]".format(PRODUCT_NAME))
