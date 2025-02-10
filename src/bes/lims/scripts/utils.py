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

import six
from bika.lims import api
from bes.lims import logger


def clear_and_rebuild(catalog_id_or_ids):
    """Clear and rebuilds the catalog or catalogs passed-in
    """
    if isinstance(catalog_id_or_ids, six.string_types):
        catalog_id_or_ids = [catalog_id_or_ids]

    for catalog_id in catalog_id_or_ids:
        logger.info("Clearing and rebuilding {} ...".format(catalog_id))
        catalog = api.get_tool(catalog_id)
        if hasattr(catalog, "clearFindAndRebuild"):
            catalog.clearFindAndRebuild()
        elif hasattr(catalog, "refreshCatalog"):
            catalog.refreshCatalog(clear=1)
        else:
            logger.warn("Cannot clear and rebuild {}".format(catalog.id))
        logger.info("Clearing and rebuilding {} [DONE]".format(catalog_id))
