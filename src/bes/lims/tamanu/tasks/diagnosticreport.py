# -*- coding: utf-8 -*-

from bes.lims.tamanu.tasks import NOTIFY_DIAGNOSTIC_REPORT
from bika.lims import api
from bika.lims.interfaces import IAnalysisRequest
from bika.lims.utils import tmpID
from senaite.core.api import dtime
from zope.component import adapter
from zope.interface import implementer

from bes.lims.tamanu import api as tapi
from bes.lims.tamanu import logger
from bes.lims.tamanu.config import ANALYSIS_STATUSES
from bes.lims.tamanu.config import LOINC_CODING_SYSTEM
from bes.lims.tamanu.config import LOINC_GENERIC_DIAGNOSTIC
from bes.lims.tamanu.config import SAMPLE_STATUSES
from bes.lims.tamanu.config import SENAITE_TESTS_CODING_SYSTEM
from bes.lims.tamanu.config import SEND_OBSERVATIONS
from bes.lims.tamanu.interfaces import ITamanuTask
from bes.lims.tamanu.tasks import queue
from bes.lims.utils import is_reportable


@adapter(IAnalysisRequest)
@implementer(ITamanuTask)
class NotifyAdapter(object):
    """Task adapter in charge of notifying Tamanu about a Diagnostic Report
    """

    def __init__(self, context):
        self.context = context

    def get_last_report(self, sample):
        """Returns the last analysis report that was created for this sample
        """
        reports_ids = sample.objectIds("ARReport")
        if not reports_ids:
            return None
        return sample.get(reports_ids[-1])

    def process(self):
        # get the last report of the sample, if any
        report = self.get_last_report(self.context)
        # send the diagnostic report
        return self.send_diagnostic_report(self.context, report)

    def send_diagnostic_report(self, sample, report, status=None):
        if not status:
            status = api.get_review_status(sample)
            if status in ["sample_received"]:
                # do not notify back unless a report was created
                if not report:
                    return None

            # handle the status to report back to Tamanu
            # registered | partial | preliminary | final | entered-in-error
            status = dict(SAMPLE_STATUSES).get(status)
            if not status:
                # any of the supported status, do nothing
                return None

        # notify about the invalidated if necessary. We can only have one
        # object linked to a given tamanu resource because of the `tamanu_uid`
        # index, for which we expect the system to always return a single
        # result on searches. Thus, we need to do this workaround here instead
        # of directly copying the tamanu resource information to the retest on
        # invalidation event
        invalidated = sample.getInvalidated()
        if invalidated:
            return self.send_diagnostic_report(invalidated, report, status=status)

        # get the tamanu session
        session = tapi.get_tamanu_session_for(sample)
        if not session:
            logger.warning("No Tamanu session attached: %r" % sample)
            return None

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
        if SEND_OBSERVATIONS:
            payload["results"] = self.get_observations(sample)

        # attach the pdf encoded in base64
        if report:
            pdf = report.getPdf()
            payload["presentedForm"] = [{
                "data": pdf.data.encode("base64"),
                "contentType": "application/pdf",
                "title": api.get_id(sample),
            }]

        # notify back to Tamanu
        return session.post("DiagnosticReport", payload)

    def get_observations(self, sample):
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


def can_notify(sample):
    """Returns whether we can notify Tamanu about this sample
    """
    if tapi.is_tamanu_content(sample):
        return True
    invalidated = sample.getInvalidated()
    if invalidated:
        return tapi.is_tamanu_content(invalidated)
    return False


def notify(sample):
    """Dispatches a diagnostic report for the given sample to Tamanu
    """
    if can_notify(sample):
        return queue.put(NOTIFY_DIAGNOSTIC_REPORT, sample)
    return False
