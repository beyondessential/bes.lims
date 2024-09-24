# -*- coding: utf-8 -*-

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
