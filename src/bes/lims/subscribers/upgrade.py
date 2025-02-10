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
from bes.lims import PRODUCT_NAME
from bes.lims.setuphandlers import setup_behaviors
from bes.lims.setuphandlers import setup_catalogs
from bes.lims.setuphandlers import setup_groups
from bes.lims.setuphandlers import setup_roles
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

    # Setup roles
    setup_roles(portal)

    # Setup groups
    setup_groups(portal)

    # Setup catalogs
    setup_catalogs(portal)

    # Add behaviors
    setup_behaviors(portal)

    # Setup workflows
    setup_workflows(portal)

    logger.info("Run {}.afterUpgradeStepHandler [DONE]".format(PRODUCT_NAME))
