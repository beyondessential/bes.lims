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
from bika.lims.workflow import getTransitionDate
from senaite.core.api import dtime
from senaite.impress.interfaces import IPdfReportStorage
from senaite.impress.publishview import PublishView
from zope.component import adapter
from zope.component import getMultiAdapter
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
        sample = self.context

        # For an invalidated Tamanu sample there is no report reflecting the
        # 'invalid' state yet (the last one, if any, predates the
        # invalidation). Generate a fresh report so the watermarked PDF added
        # by bes.lims DefaultReportView travels with the entered-in-error
        # DiagnosticReport. Report generation self-commits and calls
        # _p_jar.sync(); that is safe here because this task runs in its own
        # transaction in scripts/exec_tamanu_tasks.py, unlike the
        # workflow-event thread where it would abort the in-progress transition.
        if api.get_review_status(sample) == "invalid":
            if not self.has_current_invalid_report(sample):
                self.generate_report(sample)

        # get the last report of the sample, if any
        report = self.get_last_report(sample)
        # send the diagnostic report
        return self.send_diagnostic_report(sample, report)

    def has_current_invalid_report(self, sample):
        """Returns whether the last report already reflects the invalidated
        state of the sample, so we do not regenerate it on re-notify or on a
        task retry
        """
        report = self.get_last_report(sample)
        if not report:
            return False
        invalidated_on = getTransitionDate(
            sample, "invalidate", return_as_datetime=True)
        if not invalidated_on:
            return False
        return api.get_creation_date(report) >= invalidated_on

    def generate_report(self, sample):
        """Generates and stores a PDF report for the sample in its current
        workflow state (watermarked automatically when 'invalid') and returns
        the created ResultsReport, or None if no report could be generated
        """
        uid = api.get_uid(sample)
        request = api.get_request()
        view = PublishView(sample, request)
        reports = view.generate_reports_for([uid])
        if not reports:
            logger.warning(
                "No report generated for invalidated sample %s" % uid)
            return None
        report = reports[0]
        timestamp = dtime.DateTime().ISO()
        meta = report.get_metadata(
            contained_requests=[uid], timestamp=timestamp)
        storage = getMultiAdapter((sample, request), IPdfReportStorage)
        stored = storage.store(report.pdf, report.html, [uid], metadata=meta)
        return stored[0] if stored else None

    # _status_ is an override from diagnostic_report_status
    def send_diagnostic_report(self, sample, report, status=None):
        if not status:
            # differentiating between sample_status and diagnostic_report_status
            sample_status = api.get_review_status(sample)
            # if sample_status in ["sample_received"]:
                # do not notify back unless a report was created
                # if not report:
                #    return None

            # handle the status to report back to Tamanu
            # registered | partial | preliminary | final | entered-in-error
            status = dict(SAMPLE_STATUSES).get(sample_status)
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
            obs_list = self.get_observations(sample, sample_status = status)
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
        # notify back to Tamanu
        return session.post("Bundle", bundle, raise_for_status=True)

    def get_observations(self, sample, sample_status):
        """Returns a list of observation records suitable as a Tamanu payload
        """
        # add the observations (analyses included in the results report)
        observations = []
        for analysis in sample.getAnalyses(full_objects=True):
            if not is_reportable(analysis):
                # skip non-reportable samples
                continue

            # only report analyses that are either verified or published
            analysis_status = api.get_review_status(analysis)

            # we are also getting the sample status as analyses will remain published
            # even if the sample is invalidated
            is_sample_invalidated = sample_status == dict(SAMPLE_STATUSES).get("invalid")
            if analysis_status not in ["verified", "published"]:
                continue

            # get the representation of the analysis as a FHIR Observation
            observation = self.get_observation(analysis, is_sample_invalidated)
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

    def get_observation(self, analysis, is_sample_invalidated=None):
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
        if not is_sample_invalidated:
            status = api.get_review_status(analysis)
            status = dict(ANALYSIS_STATUSES).get(status, "partial")
        else:
            # defer to the sample's status as invalidated
            status = dict(ANALYSIS_STATUSES).get("cancelled")
        observation = {
            "resourceType": "Observation",
            "id": obs_id,
            "status": status,
            "code": ordered_test,
        }

        # get the observation's result dict
        result = self.get_observation_result(analysis)
        observation.update(result)

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

    def get_observation_result(self, analysis):
        # assign the (formatted) result; if the analysis is excluded from
        # integration, send a placeholder so the recipient knows to check
        # the PDF report for the actual result
        if analysis.getExcludeFromIntegration():
            return {"valueString": "Refer to PDF report"}

        result = analysis.getFormattedResult(html=False)
        if not self.is_quantitative(analysis):
            return {"valueString": result}

        # Uncomment after Tamanu supports `comparator` for ValueQuantity
        # See https://github.com/beyondessential/bes.lims/issues/153
        # ----->
        #if analysis.isBelowLowerDetectionLimit():
        #    ldl = analysis.getLowerDetectionLimit()
        #    unit = analysis.getUnit()
        #    quantity = self.to_quantity(ldl, unit, operator="<")
        #    return {"valueQuantity": quantity}

        #if analysis.isAboveUpperDetectionLimit():
        #    udl = analysis.getUpperDetectionLimit()
        #    unit = analysis.getUnit()
        #    quantity = self.to_quantity(udl, unit, operator=">")
        #    return {"valueQuantity": quantity}
        # <-----

        if api.is_floatable(result):
            unit = analysis.getUnit()
            quantity = self.to_quantity(result, unit)
            return {"valueQuantity": quantity}

        return {"valueString": result}

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

    def is_quantitative(self, analysis):
        """Returns whether the result for the analysis passed-in is expected to
        be quantitative or not
        """
        result_type = analysis.getResultType()
        return result_type == "numeric"

    def to_quantity(self, value, unit, operator=None):
        """Returns a representation of a quantity as a dict or None
        """
        if not api.is_floatable(value):
            return None

        quantity = {
            "value": float(value),
        }
        if unit:
            quantity.update({
                "unit": unit,
                "system": "http://unitsofmeasure.org",
                "code": unit,
            })
        if operator in ("<", "<=", ">", ">="):
            quantity["comparator"] = operator
        return quantity

    def get_reference_range(self, analysis):
        """This will return a FHIR Observation's reference range for a
        quantitative analysis.
        """
        if not self.is_quantitative(analysis):
            return None

        results_range = analysis.getResultsRange()
        if not results_range:
            return None

        reference_range = {}
        unit = analysis.getUnit()

        low = results_range.get("min")
        quantity = self.to_quantity(low, unit)
        if quantity:
            reference_range["low"] = quantity

        high = results_range.get("max")
        quantity = self.to_quantity(high, unit)
        if quantity:
            reference_range["high"] = quantity

        # TODO Toggle after Tamanu supports text for referenceRange
        range_comment = None
        # range_comment = results_range.get("rangecomment")
        if range_comment:
            reference_range["text"] = range_comment

        return [reference_range] if reference_range else None


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
