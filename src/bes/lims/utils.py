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

from bes.lims.config import ANALYSIS_REPORTABLE_STATUSES
from bika.lims import api
from bika.lims.interfaces import IAnalysisRequest
from bika.lims.interfaces import IInternalUse
from senaite.ast.config import RESISTANCE_KEY
from senaite.ast.utils import is_ast_analysis
from senaite.core.api import measure as mapi
from senaite.core.interfaces import ISampleTemplate
from senaite.core.interfaces import ISampleType


def is_reportable(analysis):
    """Returns whether the analysis has to be displayed in results reports
    """
    # do not report hidden analyses
    if analysis.getHidden():
        return False

    # do not report analyses for internal use
    if IInternalUse.providedBy(analysis):
        return False

    # do not report ast analyses, but resistance category only
    if is_ast_analysis(analysis):
        if analysis.getKeyword() != RESISTANCE_KEY:
            return False

    status = api.get_review_status(analysis)
    return status in ANALYSIS_REPORTABLE_STATUSES


def get_previous_status(instance, before=None, default=None):
    """Returns the previous state for the given instance and status from
    review history. If before is None, returns the state of the sample before
    its current status.
    """
    if not before:
        before = api.get_review_status(instance)

    # Get the review history, most recent actions first
    found = False
    history = api.get_review_history(instance)
    for item in history:
        status = item.get("review_state")
        if status == before:
            found = True
            continue
        if found:
            return status
    return default


def get_minimum_volume(obj, default="0 ml"):
    """Returns the minimum volume required for the given object
    """
    if not obj:
        return default

    min_volume = default

    if ISampleType.providedBy(obj):
        min_volume = obj.getMinimumVolume()

    elif ISampleTemplate.providedBy(obj):
        min_volume = obj.getMinimumVolume()

    elif IAnalysisRequest.providedBy(obj):
        min_volume = get_minimum_volume(obj.getTemplate(), default="")
        if not min_volume:
            min_volume = get_minimum_volume(obj.getSampleType())

    if not mapi.is_volume(min_volume):
        return default

    return min_volume


def is_enough_volume(brain_or_sample):
    """Returns whether the volume of sample is enough
    """
    obj = api.get_object(brain_or_sample)
    if not IAnalysisRequest.providedBy(obj):
        raise ValueError("Type {} is not supported".format(obj))

    # Get the expected minimum volume
    min_volume = get_minimum_volume(obj)

    # Get the sample's volume
    obj_volume = obj.getField("Volume").get(obj)

    # Convert them to magnitude and compare
    min_volume = mapi.get_magnitude(min_volume, default="0 ml")
    obj_volume = mapi.get_magnitude(obj_volume, default="0 ml")
    return obj_volume >= min_volume


def get_field_value(instance, field_name, default=None):
    """Returns the value of a Schema field
    """
    fields = api.get_fields(instance)
    field = fields.get(field_name)
    if not field:
        return default

    return field.get(instance)
