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

from bes.lims.tamanu import api as tapi
from bes.lims.tamanu.config import LOINC_CODING_SYSTEM
from bes.lims.tamanu.config import LOINC_GENERIC_DIAGNOSTIC
from bes.lims.tamanu.config import SENAITE_TESTS_CODING_SYSTEM
from bes.lims.utils import is_reportable
from bika.lims import api
from bika.lims.utils import tmpID
from senaite.core.api import dtime

SAMPLE_STATUSES = (
    # mapping between sample status and tamanu statuses
    ("sample_received", "partial"),
    ("to_be_verified", "preliminary"),
    ("verified", "preliminary"),
    ("published", "final"),
    ("invalid", "entered-in-error"),
    # Tamanu is notified back with the rejection report (Attachment) instead of
    # the results report (ARReport) on rejection.
    # See patches.bika.utils.analysisrequest.do_rejection
    # ("rejected", "cancelled"),
)

ANALYSIS_STATUSES = (
    # mapping between analyses status and tamanu statuses
    ("to_be_verified", "partial"),
    ("verified", "preliminary"),
    ("published", "final"),
)


def on_object_created(instance, event):
    """Event handler when a results report is created. Sends a POST back to
    the Tamanu instance for samples included in the report that have a Tamanu
    resource counterpart
    """
    # TODO decouple of events and do this thing in a script
    samples = instance.getContainedAnalysisRequests()
    for sample in samples:
        send_diagnostic_report(sample, instance)


def send_diagnostic_report(sample, report, status=None):
    """Notifies Tamanu instance back for this sample and report
    """
    if not status:
        status = api.get_review_status(sample)
        if status in ["sample_received"]:
            # do not notify back unless a report was created
            if not report:
                return

        # handle the status to report back to Tamanu
        # registered | partial | preliminary | final | entered-in-error
        status = dict(SAMPLE_STATUSES).get(status)
        if not status:
            # any of the supported status, do nothing
            return

    # notify about the invalidated if necessary. We can only have one object
    # linked to a given tamanu resource because of the `tamanu_uid` index, for
    # which we expect the system to always return a single result on searches
    # Thus, we need to do this workaround here instead of directly copying
    # the tamanu resource information to the retest on invalidation event
    invalidated = sample.getInvalidated()
    if invalidated:
        send_diagnostic_report(invalidated, report, status=status)

    # get the tamanu session
    session = tapi.get_tamanu_session_for(sample)
    if not session:
        return

    # get or create the uuid of the report
    report_uuid = tapi.get_uuid(tmpID())
    if report:
        report_uuid = tapi.get_uuid(report)

    # convert the uuid from hex to str
    report_uuid = str(report_uuid)

    # get the original data
    meta = tapi.get_tamanu_storage(sample)
    data = meta.get("data") or {}

    # modification date
    modified = api.get_modification_date(sample)
    if report:
        created = api.get_creation_date(report)
        modified = modified if modified > created else created
    modified = dtime.to_iso_format(modified)

    # build the payload
    # TODO Add an adapter to build payloads for a given object (e.g ARReport)
    tamanu_uid = tapi.get_tamanu_uid(sample)
    payload = {
        # meta information about the DiagnosticReport (ARReport)
        "resourceType": "DiagnosticReport",
        "id": report_uuid,
        "meta": {
            "lastUpdated": modified,
        },
        # the status of the DiagnosticReport (ARReport)
        # registered | partial | preliminary | final | entered-in-error
        "status": status,
        # the ServiceRequest(s) this ARReport is based on
        # TODO What about a DiagnosticReport with more than one basedOn
        "basedOn": [{
            "type": "ServiceRequest",
            "reference": "ServiceRequest/{}".format(tamanu_uid),
        }],
    }

    # add the test panel (profile) if set or use LOINC's generic
    # tamanu doesn't recognizes more than one coding, keep only the LOINC one
    coding = [dict(LOINC_GENERIC_DIAGNOSTIC)]
    panel = data.get("code") or {}
    for code in panel.get("coding") or []:
        if code.get("system") == LOINC_CODING_SYSTEM:
            coding = [code]
            break
    payload["code"] = {"coding": coding}

    # add the observations
    #payload["results"] = get_observations(sample)

    # attach the pdf encoded in base64
    if report:
        pdf = report.getPdf()
        payload["presentedForm"] = [{
            "data": pdf.data.encode("base64"),
            "contentType": "application/pdf",
            "title": api.get_id(sample),
        }]

    # notify back to Tamanu
    session.post("DiagnosticReport", payload)


def get_observations(sample):
    """Returns a list of observation records suitable as a Tamanu payload
    """
    # get the original data
    meta = tapi.get_tamanu_storage(sample)
    data = meta.get("data") or {}

    # group the tests (orderDetails) requested by their original id
    ordered_tests_by_key = {}
    for order_detail in data.get("orderDetail", []):
        test = tapi.get_codings(order_detail, SENAITE_TESTS_CODING_SYSTEM)
        if test:
            key = test[0].get("code")
            ordered_tests_by_key[key] = order_detail

    # add the observations (analyses included in the results report)
    observations = []
    for analysis in sample.getAnalyses(full_objects=True):
        if not is_reportable(analysis):
            # skip non-reportable samples
            continue

        # get the original LabRequest's LOINC Code
        name = api.get_title(analysis)
        keyword = analysis.getKeyword()
        ordered_test = ordered_tests_by_key.get(keyword)
        if not ordered_test:
            ordered_test = ordered_tests_by_key.get(name, {"coding": []})

        # E.g. https://hl7.org/fhir/R4B/observation-example-f001-glucose.json.html
        status = api.get_review_status(analysis)
        status = dict(ANALYSIS_STATUSES).get(status, "partial")
        observation = {
            "resourceType": "Observation",
            "status": status,
            "code": ordered_test,
        }

        # quantitative / qualitative
        if analysis.getStringResult() or analysis.getResultOptions():
            # qualitative
            observation["valueString"] = analysis.getFormattedResult()
        else:
            # quantitative
            observation["valueQuantity"] = {
                "value": analysis.getResult(),
                "unit": analysis.getUnit(),
            }

        # append the observations
        observations.append(observation)

    return observations
