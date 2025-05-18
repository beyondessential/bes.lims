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
from bes.lims import PRODUCT_NAME as product
from bes.lims.setuphandlers import setup_behaviors
from bes.lims.setuphandlers import setup_catalogs
from bes.lims.setuphandlers import setup_groups
from bes.lims.setuphandlers import setup_microbiology_department
from bes.lims.setuphandlers import setup_roles
from bes.lims.setuphandlers import setup_workflows
from bika.lims import api
from senaite.core.api import workflow as wapi
from senaite.core.catalog import ANALYSIS_CATALOG
from senaite.core.catalog import SAMPLE_CATALOG
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.migration.migrator import get_attribute_storage
from senaite.core.upgrade import upgradestep
from senaite.core.upgrade.utils import UpgradeUtils
from senaite.core.workflow import ANALYSIS_WORKFLOW
from senaite.core.workflow import SAMPLE_WORKFLOW
from zope import component
from zope.schema.interfaces import IVocabularyFactory


version = "1.0.0"  # Remember version number in metadata.xml and setup.py
profile = "profile-{0}:default".format(product)


@upgradestep(product, version)
def upgrade(tool):
    portal = tool.aq_inner.aq_parent
    ut = UpgradeUtils(portal)
    ver_from = ut.getInstalledVersion(product)

    if ut.isOlderVersion(product, version):
        logger.info("Skipping upgrade of {0}: {1} > {2}".format(
            product, ver_from, version))
        return True

    logger.info("Upgrading {0}: {1} -> {2}".format(product, ver_from, version))

    # -------- ADD YOUR STUFF BELOW --------

    logger.info("{0} upgraded to version {1}".format(product, version))
    return True


def setup_analysis_workflow(tool):
    """Adds the analysis workflow portal action
    and updates the analyses states and transitions
    """
    logger.info("Setup analysis workflow ...")

    #  Update Analyses workflow
    portal = tool.aq_inner.aq_parent
    setup = portal.portal_setup
    setup.runImportStepFromProfile(profile, "rolemap")
    setup_workflows(api.get_portal())

    # Update Analyses rolemap
    statuses = ["assigned", "unassigned"]
    query = {"portal_type": "Analysis", "review_state": statuses}
    brains = api.search(query, ANALYSIS_CATALOG)

    wf_tool = api.get_tool("portal_workflow")
    wf = wf_tool.getWorkflowById(ANALYSIS_WORKFLOW)

    for brain in brains:
        obj = api.get_object(brain)
        wf.updateRoleMappingsFor(obj)

        # Flush the object from memory
        obj._p_deactivate()

    logger.info("Setup analysis workflow [DONE]")


def setup_sampletype_behavior(tool):
    logger.info("Setup SampleType behavior ...")
    portal = tool.aq_inner.aq_parent

    # register the new behavior
    setup_behaviors(portal)

    # walk-through all sample types and update field values
    sc = api.get_tool(SETUP_CATALOG)
    for brain in sc(portal_type="SampleType"):
        obj = api.get_object(brain)
        storage = get_attribute_storage(obj)

        require_collector = storage.get("RequireCollectorOrSampler")
        obj.setRequireCollectorOrSampler(require_collector)

        container_widget = storage.get("ContainerWidget")
        if container_widget:
            obj.setContainerWidget(container_widget)

        insufficient_volume = storage.get("InsufficientVolumeText")
        if insufficient_volume:
            obj.setInsufficientVolumeText(insufficient_volume.raw)

        maximum_volume = storage.get("MaximumVolume")
        if maximum_volume:
            obj.setMaximumVolume(maximum_volume)

        obj.reindexObject()
        obj._p_deactivate()

    logger.info("Setup SampleType behavior [DONE]")


def setup_skins(tool):
    logger.info("Setup bes.lims skin layer ...")
    portal = tool.aq_inner.aq_parent
    setup = portal.portal_setup
    setup.runImportStepFromProfile(profile, "skins")
    logger.info("Setup bes.lims skin layer [DONE]")


def get_object(thing, default=None):
    try:
        return api.get_object(thing)
    except AttributeError:
        return default


def setup_scientist(tool):
    logger.info("Setup Scientist role and Scientists group ...")
    portal = tool.aq_inner.aq_parent
    setup = portal.portal_setup

    # Re-import rolemap
    setup.runImportStepFromProfile(profile, "rolemap")

    # Setup roles
    setup_roles(portal)

    # Create groups
    setup_groups(portal)

    # Update workflows
    setup_workflows(portal)

    # Update role mappings for existing samples in to_be_verified status
    query = {
        "portal_type": "AnalysisRequest",
        "review_state": "to_be_verified"
    }
    wf = wapi.get_workflow(SAMPLE_WORKFLOW)
    brains = api.search(query, SAMPLE_CATALOG)
    for brain in brains:
        sample = get_object(brain)
        if not sample:
            continue
        wf.updateRoleMappingsFor(sample)
        sample._p_deactivate()

    logger.info("Setup Scientist role and Scientists group [DONE]")


def setup_rejector(tool):
    logger.info("Setup Rejector role and Rejectors group ...")
    portal = tool.aq_inner.aq_parent
    setup = portal.portal_setup

    # Re-import rolemap
    setup.runImportStepFromProfile(profile, "rolemap")

    # Setup roles
    setup_roles(portal)

    # Create groups
    setup_groups(portal)

    # Update Analyses rolemap
    wf = wapi.get_workflow(ANALYSIS_WORKFLOW)
    states = ["assigned", "unassigned", "to_be_verified"]
    query = {"portal_type": "Analysis", "review_state": states}
    brains = api.search(query, ANALYSIS_CATALOG)
    for brain in brains:
        analysis = get_object(brain)
        if not analysis:
            continue
        wf.updateRoleMappingsFor(analysis)
        analysis._p_deactivate()

    logger.info("Setup Rejector role and Rejectors group [DONE]")


def setup_whonet_export_action(tool):
    """Adds the whonet export portal action
    """
    logger.info("Setup WHONET export ...")
    portal = tool.aq_inner.aq_parent
    setup = portal.portal_setup
    setup.runImportStepFromProfile(profile, "actions")
    logger.info("Setup WHONET export [DONE]")


def setup_department_filtering(tool):
    """Setup the indexes to enable the department filtering functionality
    """
    logger.info("Setup department filtering ...")
    portal = tool.aq_inner.aq_parent
    setup = portal.portal_setup

    # Setup Catalogs
    setup_catalogs(portal)

    logger.info("Setup department filtering [DONE]")


def setup_roles_and_groups(tool):
    """Setup bes roles and groups that went missing in newly created instances
    """
    logger.info("Setup missing roles and groups ...")
    portal = tool.aq_inner.aq_parent
    setup = portal.portal_setup

    # Re-import rolemap
    setup.runImportStepFromProfile(profile, "rolemap")

    # Setup roles
    setup_roles(portal)

    # Create groups
    setup_groups(portal)

    # Update Analyses rolemap
    wf = wapi.get_workflow(ANALYSIS_WORKFLOW)
    states = ["assigned", "unassigned", "to_be_verified"]
    query = {"portal_type": "Analysis", "review_state": states}
    brains = api.search(query, ANALYSIS_CATALOG)
    for brain in brains:
        analysis = get_object(brain)
        if not analysis:
            continue
        wf.updateRoleMappingsFor(analysis)
        analysis._p_deactivate()

    logger.info("Setup missing roles and groups [DONE]")


def reset_setup_sticker_templates(tool):
    """Restore the default sticker templates from setup
    """
    setup = api.get_setup()

    # default to the first sticker from vocabulary
    vocab_id = "senaite.core.vocabularies.stickers"
    vocab_factory = component.getUtility(IVocabularyFactory, name=vocab_id)
    vocab = list(vocab_factory(setup))
    default = vocab[0].value

    fields = [
        "AutoStickerTemplate",
        "SmallStickerTemplate",
        "LargeStickerTemplate"
    ]

    def is_from_senaite(template_id):
        """Returns whether this template is from senaite namespace
        """
        if ":" not in template_id:
            return True
        return template_id.startswith("senaite.")

    for field_name in fields:
        field = setup.getField(field_name)
        template = field.get(setup)
        if not is_from_senaite(template):
            continue

        field.set(setup, default)


def setup_ast_department(tool):
    """Setup the 'Microbiology' department for AST services and tests
    """
    logger.info("Setup department for AST services and analyses ...")
    portal = tool.aq_inner.aq_parent

    # setup microbiology department and assign the AST-like analyses to it
    setup_microbiology_department(portal)

    logger.info("Setup department for AST services and analyses [DONE]")
