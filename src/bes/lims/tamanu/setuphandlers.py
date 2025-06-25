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

from bes.lims.tamanu import logger
from senaite.core.setuphandlers import setup_core_catalogs
from senaite.core.setuphandlers import setup_other_catalogs

UID_CATALOG = "uid_catalog"

# Add-on specific Catalogs (list of core's BaseCatalog objects)
CATALOGS = (
)

# Tuples of (catalog, index_name, index_attribute, index_type)
INDEXES = [
    (UID_CATALOG, "tamanu_uid", "tamanu_uid", "FieldIndex"),
]

# Tuples of (catalog, column_name)
COLUMNS = [
]


def setup_catalogs(portal):
    """Setup new catalogs and modifications to existing ones
    """
    logger.info("Setup Catalogs ...")
    setup_core_catalogs(portal, catalog_classes=CATALOGS)
    setup_other_catalogs(portal, indexes=INDEXES, columns=COLUMNS)
    logger.info("Setup Catalogs [DONE]")
