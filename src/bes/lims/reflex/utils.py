# -*- coding: utf-8 -*-

from bika.lims import api
from senaite.core.catalog import SETUP_CATALOG


def get_service(keyword):
    """Returns the Analysis Service for the given keyword, if any
    """
    service = None
    query = {
        "portal_type": "AnalysisService",
        "getKeyword": keyword
    }
    brains = api.search(query, SETUP_CATALOG)
    if len(brains) == 1:
        service = api.get_object(brains[0])
    return service


def new_analysis_id(sample, analysis_keyword):
    """Returns a new analysis id for an hypothetic new test with given keyword
    to prevent clashes with ids of other analyses from same sample
    """
    new_id = analysis_keyword
    analyses = sample.getAnalyses(getKeyword=analysis_keyword)
    if analyses:
        new_id = "{}-{}".format(analysis_keyword, len(analyses))
    return new_id


def get_organisms_vocabulary(empty=None, **kwargs):
    """Returns a vocabulary of organisms items based on the search criteria
    passed-in. By default, if not kwargs are specified, returns the list of
    active Microorganisms sorted by title, ascending
    :param empty: text for the empty option to be returned in first place. If
        the value of empty is None, does not add an empty option
    """
    query = {
        "is_active": True,
        "sort_on": "sortable_title",
        "sort_order": "ascending"
    }
    query.update(kwargs)
    query["portal_type"] = "Microorganism"

    # Search the organisms and build the list of options
    organisms = map(api.get_title, api.search(query, SETUP_CATALOG))

    # Insert the empty value, if any
    if empty is not None:
        organisms.insert(0, empty)

    return organisms
