# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# BES.LIMS is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright 2024-2025 by it's authors.
# Some rights reserved, see README and LICENSE.

from bes.lims.tamanu import logger
from bika.lims import api
from bika.lims.api import security as sapi
from bika.lims.utils.analysisrequest import create_analysisrequest as create_sample
from bika.lims.workflow import doActionFor
from Products.CMFCore.permissions import ModifyPortalContent
from senaite.core.catalog import CLIENT_CATALOG
from senaite.core.catalog import CONTACT_CATALOG
from senaite.core.catalog import SETUP_CATALOG

import transaction


# FHIR priority -> SENAITE priority code
PRIORITIES = {
    "stat": "1",
    "asap": "3",
    "routine": "5",
}

# FHIR ServiceRequest statuses to skip on first creation
SKIP_STATUSES = (
    "revoked", "draft", "entered-in-error", "completed"
)

# FHIR status -> SENAITE workflow transition
TRANSITIONS = {
    "revoked": "cancel",
    "entered-in-error": "reject",
}

# Physical-type code that marks a Ward in Encounter.location
WARD_PHYSICAL_TYPE_CODE = "wa"


class BundleImporter(object):
    """Processes a BundleResource and creates/edits SENAITE objects.

    Keeps all SENAITE/Zope-dependent logic in one place so BundleResource
    itself remains environment-agnostic.

    Usage::

        importer = BundleImporter(bundle)
        importer.run(dry_run=True)   # log only
        importer.run()               # write to SENAITE
    """

    def __init__(self, bundle):
        self.bundle = bundle

    def run(self, dry_run=False):
        """Process all ServiceRequests in the bundle.

        Delegates to bundle.process() so the iteration and error handling
        live in one place.

        :param dry_run: when True, log what would happen without writing.
        :returns: tuple of (ok, errors) counts.
        """
        self._log_summary()
        ok, errors = self.bundle.process(
            "ServiceRequest",
            self._process_service_request,
            dry_run=dry_run,
        )
        logger.info("Done - ok: {0}  errors: {1}".format(ok, errors))
        return ok, errors

    # ------------------------------------------------------------------
    # Root processor  (called once per ServiceRequest by bundle.process)
    # ------------------------------------------------------------------

    def _process_service_request(self, sr, dry_run=False):
        """Process a single ServiceRequest resource.

        All other resources (Patient, Specimen, Encounter, etc.) are
        reached by walking sr's own accessors -- the bundle index resolves
        them transparently.
        """
        if dry_run:
            self._log_dry_run(sr)
            return

        self._write_service_request(sr)

    # ------------------------------------------------------------------
    # SENAITE write path
    # ------------------------------------------------------------------

    def _write_service_request(self, sr):
        sr_id = sr.UID

        # Client -- via ServiceRequest -> Encounter -> Organization
        org = sr.getServiceProvider()
        if not org:
            logger.error("SR {0}: cannot resolve Organization - skipping".format(sr_id))
            return
        client = self._resolve_client(org)
        if not client:
            logger.error("SR {0}: cannot resolve Client - skipping".format(sr_id))
            return

        # Contact -- Practitioner (requester)
        requester = sr.getRequester()
        contact = self._resolve_contact(requester, client) if requester else None

        # Specimen
        specimen = sr.getSpecimen()
        if not specimen:
            logger.info("SR {0}: specimen missing - skipping".format(sr_id))
            return
        sample_type = self._resolve_sample_type(specimen)
        if not sample_type:
            logger.error("SR {0}: cannot resolve SampleType - skipping".format(sr_id))
            return
        sample_point = self._resolve_sample_point(specimen)
        date_sampled = specimen.get_date_sampled()
        collector = specimen.getCollectorName()

        # Ward -- via Encounter locations
        encounter = sr.getEncounter()
        ward = self._resolve_ward(encounter) if encounter else None

        # Patient fields
        patient_resource = sr.getPatientResource()
        p_info = patient_resource.to_object_info() if patient_resource else {}

        # Analysis services from orderDetail
        services = self._resolve_services(sr)

        priority = PRIORITIES.get(sr.get_raw("priority", "routine"), "5")
        notes = sr.get_raw("note") or []
        clinical_info = "\n".join(
            n.get("text", "") for n in notes if n.get("text")
        )

        sample_values = {
            "Client": client,
            "Contact": contact,
            "SampleType": sample_type,
            "SamplePoint": sample_point,
            "DateSampled": date_sampled,
            "Priority": priority,
            "Collector": collector,
            "Sampler": collector,
            "ClinicalInformation": clinical_info,
            "Ward": ward,
            "MedicalRecordNumber": {"value": p_info.get("mrn", "")},
            "PatientFullName": {
                "firstname": p_info.get("firstname", ""),
                "middlename": p_info.get("middlename", ""),
                "lastname": p_info.get("lastname", ""),
            },
            "DateOfBirth": p_info.get("birthdate"),
            "Sex": p_info.get("sex", ""),
        }

        # sr.getObject() calls get_object_by_tamanu_uid(sr.UID) -- returns an
        # existing sample once linked via tapi.link_tamanu_resource()
        sample = sr.getObject()
        request = api.get_request() or api.get_test_request()

        if sample:
            self._edit_sample(sample, **sample_values)
            logger.info("Edited sample for SR {0}: {1!r}".format(sr_id, sample))
        else:
            if sr.status in SKIP_STATUSES:
                logger.info("Skip SR {0} - status '{1}'".format(sr_id, sr.status))
                return
            sample = create_sample(client, request, sample_values, services)
            logger.info("Created sample for SR {0}: {1!r}".format(sr_id, sample))

        action = TRANSITIONS.get(sr.status)
        if action:
            doActionFor(sample, action)
            logger.info("Transition '{0}' applied to {1!r}".format(action, sample))

        transaction.commit()

    # ------------------------------------------------------------------
    # SENAITE object resolvers
    # ------------------------------------------------------------------

    def _resolve_client(self, org_resource):
        """Find or create a SENAITE Client from an Organization resource."""
        info = org_resource.to_object_info()
        name = info.get("title") or info.get("Name", "")
        if not name:
            return None

        brains = api.search(
            {"portal_type": "Client", "title": name,
             "sort_on": "created", "sort_order": "descending"},
            CLIENT_CATALOG,
        )
        if brains:
            return api.get_object(brains[0])

        container = api.get_portal().clients
        return api.create(container, "Client", **info)

    def _resolve_contact(self, practitioner_resource, client):
        """Find or create a SENAITE Contact from a Practitioner resource."""
        info = practitioner_resource.to_object_info()
        firstname = info.get("Firstname", "")
        lastname = info.get("Surname", "")
        fullname = "{} {}".format(firstname, lastname).strip()
        if not fullname:
            return None

        brains = api.search(
            {"portal_type": "Contact",
             "getFullname": fullname,
             "getParentUID": api.get_uid(client),
             "sort_on": "created", "sort_order": "descending"},
            CONTACT_CATALOG,
        )
        if brains:
            return api.get_object(brains[0])

        return api.create(client, "Contact", **info)

    def _resolve_sample_type(self, specimen_resource):
        """Find or create a SENAITE SampleType via SpecimenResource."""
        sample_type = specimen_resource.get_sample_type()
        if sample_type:
            return sample_type

        info = specimen_resource.get_sample_type_info()
        if not info.get("title"):
            return None
        container = api.get_senaite_setup().sampletypes
        return api.create(container, "SampleType", **info)

    def _resolve_sample_point(self, specimen_resource):
        """Find or create a SENAITE SamplePoint via SpecimenResource."""
        sample_point = specimen_resource.get_sample_point()
        if sample_point:
            return sample_point

        info = specimen_resource.get_sample_point_info()
        if not info.get("title"):
            return None
        container = api.get_senaite_setup().samplepoints
        return api.create(container, "SamplePoint", **info)

    def _resolve_ward(self, encounter_resource):
        """Find or create a SENAITE Ward from Encounter location entries."""
        if "Ward" not in api.get_portal_types():
            return None

        locations = encounter_resource.getLocations(
            form=WARD_PHYSICAL_TYPE_CODE
        )
        if not locations:
            return None

        last = locations[-1]
        location_ref = last.get("location") or {}
        name = location_ref.get("display")
        if not name:
            return None

        brains = api.search(
            {"portal_type": "Ward", "title": name,
             "sort_on": "created", "sort_order": "descending"},
            SETUP_CATALOG,
        )
        if brains:
            return api.get_object(brains[0])

        container = api.get_setup().wards
        return api.create(container, "Ward", title=name)

    def _resolve_services(self, sr_resource):
        """Return AnalysisService objects for test codes in orderDetail."""
        by_keyword = {}
        for brain in api.search({"portal_type": "AnalysisService"}, SETUP_CATALOG):
            obj = api.get_object(brain)
            by_keyword[obj.getKeyword()] = obj

        services = []
        for detail in sr_resource.get_raw("orderDetail") or []:
            for param in detail.get("parameter", []):
                param_codings = param.get("code", {}).get("coding", [])
                if not any(c.get("code") == "LOINC" for c in param_codings):
                    continue
                for vc in param.get("valueCodeableConcept", {}).get("coding", []):
                    code = vc.get("code", "")
                    service = by_keyword.get(code)
                    if service:
                        services.append(service)
                    else:
                        logger.warning(
                            "No AnalysisService for LOINC {0} ({1})".format(
                                code, vc.get("display", "")))
        return services

    def _edit_sample(self, sample, **kwargs):
        """Wrapper around api.edit that drops read-only/unpermissioned fields."""
        fields = api.get_fields(sample)
        for field_name, field in fields.items():
            if getattr(field, "readonly", False):
                kwargs.pop(field_name, None)
            perm = getattr(field, "write_permission", ModifyPortalContent)
            if perm and not sapi.check_permission(perm, sample):
                kwargs.pop(field_name, None)
        api.edit(sample, **kwargs)

    # ------------------------------------------------------------------
    # Dry-run logging
    # ------------------------------------------------------------------

    def _log_summary(self):
        bundle = self.bundle
        logger.info("Bundle contents:")
        logger.info("  Patient(s)       : {0}".format(len(bundle.getPatients())))
        logger.info("  Organization(s)  : {0}".format(len(bundle.getOrganizations())))
        logger.info("  Practitioner(s)  : {0}".format(len(bundle.getPractitioners())))
        logger.info("  Specimen(s)      : {0}".format(len(bundle.getSpecimens())))
        logger.info("  ServiceRequest(s): {0}".format(
            len(bundle.getServiceRequests())))

    def _log_dry_run(self, sr):
        """Pretty-print what would be created/edited for a ServiceRequest."""
        patient = sr.getPatientResource()
        p_info = patient.to_object_info() if patient else {}

        org = sr.getServiceProvider()
        org_info = org.to_object_info() if org else {}

        requester = sr.getRequester()
        pract_info = requester.to_object_info() if requester else {}

        specimen = sr.getSpecimen()
        specimen_type_info = specimen.get_sample_type_info() if specimen else {}
        date_sampled = specimen.get_date_sampled() if specimen else None

        encounter = sr.getEncounter()

        test_lines = []
        for detail in sr.get_raw("orderDetail") or []:
            for param in detail.get("parameter", []):
                if not any(c.get("code") == "LOINC"
                           for c in param.get("code", {}).get("coding", [])):
                    continue
                for vc in param.get("valueCodeableConcept", {}).get("coding", []):
                    test_lines.append("{0}  {1}".format(
                        vc.get("code", ""), vc.get("display", "")))

        logger.info("")
        logger.info("  [DRY] ServiceRequest: {0}".format(sr.UID))
        logger.info("  " + "-" * 56)
        logger.info("  Patient")
        logger.info("    MRN       : {0}".format(p_info.get("mrn", "")))
        logger.info("    Name      : {0} {1} {2}".format(
            p_info.get("firstname", ""),
            p_info.get("middlename", ""),
            p_info.get("lastname", "")))
        logger.info("    DOB       : {0}".format(p_info.get("birthdate", "")))
        logger.info("    Sex       : {0}".format(p_info.get("sex", "")))
        logger.info("  Client (Organization)")
        logger.info("    Name      : {0}".format(org_info.get("title", "")))
        logger.info("  Contact (Practitioner)")
        logger.info("    Name      : {0} {1}".format(
            pract_info.get("Firstname", ""),
            pract_info.get("Surname", "")))
        logger.info("  Encounter / Ward")
        logger.info("    Encounter : {0}".format(
            encounter.UID if encounter else "not resolved"))
        logger.info("  Specimen")
        logger.info("    Type      : {0}  ({1})".format(
            specimen_type_info.get("prefix", ""),
            specimen_type_info.get("title", "")))
        logger.info("    Collected : {0}".format(date_sampled or ""))
        logger.info("  Tests ({0})".format(len(test_lines)))
        for line in test_lines:
            logger.info("    {0}".format(line))
        logger.info("  SENAITE sample fields")
        logger.info("    Priority  : {0}".format(
            PRIORITIES.get(sr.get_raw("priority", "routine"), "5")))
        logger.info("    Status    : {0}".format(sr.status or ""))
        logger.info("")
