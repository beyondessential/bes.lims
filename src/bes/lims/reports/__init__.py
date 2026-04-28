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

from datetime import datetime

from bes.lims.config import TARGET_PATIENTS
from bes.lims.utils import get_field_value
from bes.lims.utils import get_file_resource
from bes.lims.utils import read_csv
from bika.lims import api
from senaite.ast.utils import get_identified_microorganisms
from senaite.core.api import dtime
from senaite.core.catalog import ANALYSIS_CATALOG
from senaite.core.catalog import SAMPLE_CATALOG


def get_received_samples(from_date, to_date, **kwargs):
    """Returns the primary samples (no Partitions) that were received within
    the passed-in date range and parameters
    """
    query = {
        "portal_type": "AnalysisRequest",
        "isRootAncestor": True,
        "getDateReceived": {
            "query": [from_date, to_date],
            "range": "min:max"
        },
        "sort_on": "getDateReceived",
        "sort_order": "ascending",
    }
    query.update(**kwargs)
    return api.search(query, SAMPLE_CATALOG)


def get_received_samples_by_year(year, **kwargs):
    """Returns the primary samples received within the passed-in year and
    parameters
    """
    from_date = dtime.date_to_string(datetime(year, 1, 1))
    to_date = dtime.date_to_string(datetime(year, 12, 31))
    return get_received_samples(from_date, to_date, **kwargs)


def group_by(objs, func):
    """Group objects by the passed-in function
    """
    groups = {}
    for obj in objs:
        value = None
        if callable(func):
            value = func(obj)
        elif hasattr(obj, func):
            value = getattr(obj, func, None)
        elif api.is_brain(obj):
            brain_obj = api.get_object(obj)
            value = getattr(brain_obj, func, None)

        if callable(value):
            value = value()

        if api.is_object(value):
            # group by title
            value = api.get_title(value)

        elif dtime.is_d(value) or dtime.is_dt(value) or dtime.is_DT(value):
            # group by month
            value = dtime.to_DT(value)
            value = int(value.month())

        elif not value and value != 0:
            # handle Missing.Value properly
            value = None

        if isinstance(value, list):
            # in case value is a list of rejection reasons
            map(lambda val: groups.setdefault(val, []).append(obj), value)
        else:
            groups.setdefault(value, []).append(obj)
    return groups


def count_by(objs, func):
    """Count objects by the passed-in function
    """
    counts = {}
    groups = group_by(objs, func)
    for key, matches in groups.items():
        counts[key] = len(matches)
    return counts


def get_percentage(num, total, ndigits=2):
    """Returns the percentage rate of num from the total
    """
    rate = 0.0
    if all([num, total]):
        rate = float(num) / total
    return round(100 * rate, ndigits)


def get_analyses(from_date, to_date, **kwargs):
    """Returns the analyses that were received within the passed-in date range
    """
    query = {
        "portal_type": "Analysis",
        "getDateReceived": {
            "query": [from_date, to_date],
            "range": "min:max"
        },
        "sort_on": "getDateReceived",
        "sort_order": "ascending",
    }
    query.update(**kwargs)
    return api.search(query, ANALYSIS_CATALOG)


def get_analyses_by_year(year, **kwargs):
    """Returns the analyses received within the passed-in year
    """
    from_date = dtime.date_to_string(datetime(year, 1, 1))
    to_date = dtime.date_to_string(datetime(year, 12, 31))
    return get_analyses(from_date, to_date, **kwargs)


def calculate_rate(total_samples, matched_samples):
    """Calculate the rate of matched samples in total samples
    """
    rate = 0
    if total_samples > 0:
        rate = 100 * float(matched_samples) / total_samples
    return round(rate, 2)


def is_matched_microorganisms_sample(microorganisms, sample):
    """Checks whether the sample contains the microorganisms that in
    target microorganisms list.
    """
    # TODO Cleanup
    # Get the names of the selected microorganisms
    sample_microorganisms = get_identified_microorganisms(sample)
    sample_microorganisms = [api.get_title(m) for m in sample_microorganisms]

    if any(item in microorganisms for item in sample_microorganisms):
        return True
    return False


def get_matched_microorganisms_sample(microorganisms, samples):
    """Returns the samples with growth of potential pathogens
    """
    # TODO Cleanup
    matched_microorganisms_samples = filter(
        lambda sample: is_matched_microorganisms_sample(microorganisms, sample),  # noqa: E501
        samples
    )

    return matched_microorganisms_samples


def get_potential_true_pathogen_microorganisms():
    """Returns the potential true pathogens microorganisms that read from csv
    """
    # TODO Cleanup
    microorganisms_file = get_file_resource(
        "potential_true_pathogen_microorganisms.csv"
    )
    microorganisms = read_csv(microorganisms_file)
    pathogen_microorganisms = [
        microorganism.get("Title") for microorganism in microorganisms
        if microorganism.get(
            "Potential true pathogen in blood specimen"
        ) == "Yes"
    ]
    return pathogen_microorganisms


def is_matched_target_patient(target_patient, sample):
    """Checks whether the sample is match with target patient
    """
    # TODO Cleanup
    bottles = get_field_value(sample, "Bottles")
    container_bottles = [bottle["Container"] for bottle in bottles]
    if (
        TARGET_PATIENTS.getValue(target_patient) == "Adult patient" and
        "Aerobic Blood Bottle" in container_bottles and
        "Anaerobic Blood Bottle" in container_bottles
    ):
        return True
    elif (
        TARGET_PATIENTS.getValue(target_patient) == "Paediatric patient" and
        "Aerobic Blood Bottle" in container_bottles and
        "Anaerobic Blood Bottle" not in container_bottles
    ):
        return True

    return False


def get_target_patient_samples(target_patient, samples):
    """Returns the samples that matched with target patient
    """
    # TODO Cleanup
    target_patient_samples = filter(
        lambda sample: is_matched_target_patient(target_patient, sample),
        samples
    )

    return target_patient_samples
