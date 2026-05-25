# -*- coding: utf-8 -*-

import copy
import uuid

from bes.lims.tamanu import api as tapi
from bes.lims.tamanu import logger
from bes.lims.tamanu.config import ANALYSIS_STATUSES
from bes.lims.tamanu.config import LOINC_CODING_SYSTEM
from bes.lims.tamanu.config import LOINC_GENERIC_DIAGNOSTIC
from bes.lims.tamanu.config import SAMPLE_STATUSES
from bes.lims.tamanu.config import SENAITE_TESTS_CODING_SYSTEM
from bes.lims.tamanu.config import SEND_OBSERVATIONS
from bes.lims.tamanu.config import SNOMED_CODING_SYSTEM
from bes.lims.tamanu.interfaces import ITamanuTask
from bes.lims.tamanu.tasks import NOTIFY_DIAGNOSTIC_REPORT
from bes.lims.tamanu.tasks import queue
from bes.lims.utils import is_reportable
from bika.lims import api
from bika.lims.interfaces import IAnalysisRequest
from bika.lims.utils import tmpID
from senaite.core.api import dtime
from zope.component import adapter
from zope.interface import implementer


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
        reports = sample.getReports()
        if not reports:
            return None
        return reports[-1]

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
                # does not match any of the supported statuses, do nothing
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
        # TODO Add an adapter to build payloads for a given object
        tamanu_uid = tapi.get_tamanu_uid(sample)
        payload = {
            # meta information about the DiagnosticReport (ResultsReport)
            "resourceType": "DiagnosticReport",
            "id": report_uuid,
            "meta": {
                "lastUpdated": modified,
            },
            # the status of the DiagnosticReport (ResultsReport)
            # registered | partial | preliminary | final | entered-in-error
            "status": status,
            # the ServiceRequest(s) this ResultsReport is based on
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

        # add subject if available
        subject = data.get("subject")
        if subject:
            payload["subject"] = subject

        # prepare observations
        obs_refs = []
        entries = []
        if SEND_OBSERVATIONS:
            obs_list = self.get_observations(sample)
            for obs_id, obs in obs_list:
                display = obs.get("code", {}).get("text", "")
                obvs_reference = "Observation/{}".format(obs_id)
                obvs_entry = {
                    # TODO Might not be required, check with Rohan
                    "fullUrl": obvs_reference,
                    "resource": obs,
                    # TODO Might not be required, check with Rohan
                    "request": {
                        "method": "POST",
                        "url": obvs_reference,
                    },
                }
                obs_refs.append({"reference": obvs_reference, "display": display})
                entries.append(obvs_entry)
            payload["result"] = obs_refs

        # attach the pdf encoded in base64
        if report:
            pdf = report.getPdf()
            payload["presentedForm"] = [{
                "data": pdf.data.encode("base64"),
                "contentType": "application/pdf",
                "language": "en",
                "title": api.get_id(sample),
            }]

        # create the diagnostic report entry
        diag_reference =  "DiagnosticReport/{}".format(report_uuid)
        diag_entry = {
            # TODO Might not be required, check with Rohan
            "fullUrl": diag_reference,
            "resource": payload,
            # TODO Might not be required, check with Rohan
            "request": {
                "method": "POST",
                "url": diag_reference,
            },
        }
        entries.insert(0, diag_entry)

        # build the bundle
        bundle_id = str(uuid.uuid4())
        bundle = {
            "resourceType": "Bundle",
            "id": bundle_id,
            "type": "transaction",
            "entry": entries
        }
        import pdb; pdb.set_trace()
        # notify back to Tamanu
        return session.post("Bundle", bundle, raise_for_status=True)

    def get_observations(self, sample):
        """Returns a list of observation records suitable as a Tamanu payload
        """
        # add the observations (analyses included in the results report)
        observations = []
        for analysis in sample.getAnalyses(full_objects=True):
            if not is_reportable(analysis):
                # skip non-reportable samples
                continue

            # only report analyses that are either verified or published
            status = api.get_review_status(analysis)
            if status not in ["verified", "published"]:
                continue

            # get the representation of the analysis as a FHIR Observation
            observation = self.get_observation(analysis)
            # append the observations
            observations.append((observation["id"], observation))
        return observations

    def get_observation_method(self, analysis):
        """Returns the method if one exists of the particular
        Observation
        """
        method = analysis.getMethod()

        # method.Title() is mandatory
        if method and method.getMethodID():
            return {
                "coding": [{
                    "system": SNOMED_CODING_SYSTEM,
                    "code": method.getMethodID(),
                    "display": method.Title(),
                }]
            }
        return None

    def get_observation(self, analysis):
        """Returns a dict that represents a FHIR Observation counterpart of the
        analysis passed-in
        """
        # generate unique ID for the observation
        obs_id = str(tapi.get_uuid(analysis))

        # get the test ordered initially in the FHIR ServiceRequest
        ordered_test = self.get_order_detail(analysis)
        if not ordered_test:
            # Although not initially requested, we also report this analysis
            # and its result back to Tamanu as an Observation!
            keyword = analysis.getKeyword()
            name = api.get_title(analysis)
            display = "%s | %s" % (keyword, name)
            coding =  {
                "code": keyword,
                "system": SENAITE_TESTS_CODING_SYSTEM,
                "display": display
            }
            ordered_test = {"coding": [coding]}
        # E.g. https://hl7.org/fhir/R4B/observation-example-f001-glucose.json.html
        status = api.get_review_status(analysis)
        status = dict(ANALYSIS_STATUSES).get(status, "partial")
        observation = {
            "resourceType": "Observation",
            "id": obs_id,
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
        reference_range = self.get_reference_range(analysis)
        if reference_range:
            observation["referenceRange"] = reference_range

        # assign the person who verified the analysis (performer)
        performer = self.get_performer(analysis)
        if performer:
            observation["performer"] = performer

        method = self.get_observation_method(analysis)
        if method:
            observation["method"] = method

        return observation

    def get_order_detail(self, analysis):
        """Returns the orderDetail of the initial ServiceRequest that
        originated the analysis passed-in, if any. It searches for the first
        orderDetail whose code matches with the analysis keyword. If no
        orderDetail by analysis keyword is found, it falls-back to a search by
        analysis name.
        """
        # get the original ServiceRequest FHIR resource dict
        sample = analysis.getRequest()
        meta = tapi.get_tamanu_storage(sample)

        # group the tests by code
        tests = dict()
        data = meta.get("data") or {}
        for order_detail in data.get("orderDetail", []):
            test = tapi.get_codings(order_detail, SENAITE_TESTS_CODING_SYSTEM)
            code = test[0].get("code") if test else None
            if not code:
                continue
            if code in tests:
                # only interested on the first test
                continue
            tests[code] = order_detail

        # find matches by keyword
        keyword = analysis.getKeyword()
        match = tests.get(keyword)
        if not match:
            # fallback to match by name
            name = api.get_title(analysis)
            match = tests.get(name)

        return copy.deepcopy(match)

    def get_performer(self, analysis):
        """Return a FHIR performer list of the user who verified the analysis
        passed-in, suitable for the injection in a FHIR resource (Observation)
        """
        # Adding the verificator to the performer of the Observation
        verificators = analysis.getVerificators()

        # The last one is the final verifier
        user_id = verificators[-1] if verificators else None
        if not user_id:
            # not yet verified?
            return None

        # Get the fullname if there is one assigned for this user
        display = api.get_user_fullname(user_id) or user_id
        return [{
            "display": display,
            "identifier": {
                "value": user_id,
            }
        }]

    def get_reference_range(self, analysis):
        """This will return a FHIR Observation's reference range for a
        quantitative analysis.
        """
        # including this duplicated check in case function is reused
        results_range = analysis.getResultsRange()
        if not results_range:
            return None

        range_comment = results_range.get("rangecomment")
        low = results_range.get("min")
        high = results_range.get("max")

        if not low and not high and not range_comment:
            return None

        unit = analysis.getUnit()
        reference_range = {}

        def make_quantity(value):
            try:
                quantity = {"value": float(value)}
            except (TypeError, ValueError):
                return None
            if unit:
                quantity.update({
                    "unit": unit,
                    "system": "http://unitsofmeasure.org",
                    "code": unit,
                })
            return quantity

        if low:
            quantity = make_quantity(low)
            if quantity:
                reference_range["low"] = quantity

        if high:
            quantity = make_quantity(high)
            if quantity:
                reference_range["high"] = quantity

        if range_comment:
            reference_range["text"] = range_comment

        return [reference_range]


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
        return queue.put(NOTIFY_DIAGNOSTIC_REPORT, sample, delay=300)
    return False
