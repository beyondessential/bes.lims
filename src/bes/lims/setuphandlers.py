# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# Copyright 2024 Beyond Essential Systems Pty Ltd

from bes.lims import logger
from senaite.core.setuphandlers import setup_core_catalogs
from senaite.core.setuphandlers import setup_other_catalogs
from senaite.core.catalog import ANALYSIS_CATALOG
from senaite.core.catalog import SAMPLE_CATALOG


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


def setup_handler(context):
    """Setup handler
    """

    if context.readDataFile("bes.lims.txt") is None:
        return

    logger.info("BES setup handler [BEGIN]")

    portal = context.getSite()

    # Setup Catalogs
    setup_catalogs(portal)

    logger.info("BES setup handler [DONE]")


def setup_catalogs(portal):
    """Setup catalogs
    """
    logger.info("Setup Catalogs ...")

    setup_core_catalogs(portal, catalog_classes=CATALOGS)
    setup_other_catalogs(portal, indexes=INDEXES, columns=COLUMNS)

    logger.info("Setup Catalogs [DONE]")
