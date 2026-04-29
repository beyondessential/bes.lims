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
from bes.lims.tamanu.resources import TamanuResource
from bes.lims.tamanu.resources.encounter import Encounter
from bes.lims.tamanu.resources.organization import Organization
from bes.lims.tamanu.resources.patient import PatientResource
from bes.lims.tamanu.resources.practitioner import Practitioner
from bes.lims.tamanu.resources.servicerequest import ServiceRequest
from bes.lims.tamanu.resources.specimen import SpecimenResource


# Maps FHIR resourceType strings to their resource wrapper classes.
# Extend this dict when new resource types are added to the IG.
RESOURCE_CLASS_MAP = {
    "Encounter": Encounter,
    "Organization": Organization,
    "Patient": PatientResource,
    "Practitioner": Practitioner,
    "ServiceRequest": ServiceRequest,
    "Specimen": SpecimenResource,
}


class BundleResource(TamanuResource):
    """Wraps a FHIR Bundle and acts as its own session.

    BundleResource serves two roles at once:

    1. **Resource** -- it extends TamanuResource so it fits naturally into the
       existing resource hierarchy and can be passed wherever a resource is
       expected.

    2. **Session** -- TamanuResource.get_reference() calls
       ``self._session.get(ref_id)`` and ``self._session.to_resource(data)``
       to follow references.  By passing *itself* as the session, all
       contained resources resolve their cross-references against the Bundle's
       in-memory index rather than making HTTP calls.

    Usage::

        bundle = BundleResource(data)

        # Iterate directly
        for sr in bundle.getServiceRequests():
            patient  = sr.getPatientResource()   # resolved from bundle
            specimen = sr.getSpecimen()           # resolved from bundle
            org      = sr.getServiceProvider()    # resolved from bundle

        # Or drive processing through the bundle itself
        ok, errors = bundle.process("ServiceRequest", my_processor, dry_run=True)
    """

    def __init__(self, data):
        # Pass self as the session so nested resources call back into us
        super(BundleResource, self).__init__(session=self, data=data)
        self._index = self._build_index(data)

    # ------------------------------------------------------------------
    # Internal index
    # ------------------------------------------------------------------

    def _build_index(self, data):
        """Index all entries by fullUrl and by ResourceType/id."""
        index = {}
        self._resources = []  # deduplicated list of raw resource dicts

        for entry in data.get("entry", []):
            resource = entry.get("resource", {})
            full_url = entry.get("fullUrl", "")
            rtype = resource.get("resourceType", "")
            rid = resource.get("id", "")

            if full_url:
                index[full_url] = resource
            if rtype and rid:
                index["{}/{}".format(rtype, rid)] = resource

            # Track each resource once for iteration
            if rtype:
                self._resources.append(resource)

        return index

    # ------------------------------------------------------------------
    # Session interface (called by TamanuResource.get_reference)
    # ------------------------------------------------------------------

    def get(self, ref_id):
        """Resolve a reference string to a raw resource dict.

        Accepts:
          - urn:uuid style fullUrls   e.g. "urn:uuid:ddaf107d-..."
          - ResourceType/id           e.g. "Patient/ddaf107d-..."
          - Absolute URLs used as fullUrl

        Returns the raw dict, or None if the reference cannot be resolved.
        """
        resource = self._index.get(ref_id)
        if resource:
            return resource

        # Last resort: treat the final two path segments as ResourceType/id
        parts = ref_id.rstrip("/").split("/")
        if len(parts) >= 2:
            resource = self._index.get("{}/{}".format(parts[-2], parts[-1]))
            if resource:
                return resource

        logger.warning("BundleResource: cannot resolve reference {!r}".format(
            ref_id))
        return None

    def to_resource(self, data):
        """Wrap a raw resource dict in the appropriate resource class.

        Uses RESOURCE_CLASS_MAP to pick the class. Unknown resourceTypes
        fall back to the plain TamanuResource so nothing hard-crashes.
        """
        if not data:
            return None
        rtype = data.get("resourceType", "")
        cls = RESOURCE_CLASS_MAP.get(rtype, TamanuResource)
        if cls is TamanuResource:
            logger.warning(
                "BundleResource: no specific class for resourceType={!r}, "
                "using TamanuResource".format(rtype))
        return cls(self, data)

    # ------------------------------------------------------------------
    # Bundle-level accessors
    # ------------------------------------------------------------------

    @property
    def bundle_type(self):
        """Returns the Bundle type (e.g. 'transaction', 'collection')."""
        return self.get_raw("type")

    def get_all(self, resource_type):
        """Return all wrapped resources of a given FHIR resourceType."""
        cls = RESOURCE_CLASS_MAP.get(resource_type, TamanuResource)
        return [
            cls(self, resource)
            for resource in self._resources
            if resource.get("resourceType") == resource_type
        ]

    # -- typed convenience accessors ------------------------------------

    def getServiceRequests(self):
        """Return all ServiceRequest resources in the Bundle."""
        return self.get_all("ServiceRequest")

    def getPatients(self):
        """Return all Patient resources in the Bundle."""
        return self.get_all("Patient")

    def getOrganizations(self):
        """Return all Organization resources in the Bundle."""
        return self.get_all("Organization")

    def getPractitioners(self):
        """Return all Practitioner resources in the Bundle."""
        return self.get_all("Practitioner")

    def getSpecimens(self):
        """Return all Specimen resources in the Bundle."""
        return self.get_all("Specimen")

    def getEncounters(self):
        """Return all Encounter resources in the Bundle."""
        return self.get_all("Encounter")


    # ------------------------------------------------------------------
    # TamanuResource overrides
    # ------------------------------------------------------------------

    def to_object_info(self):
        """Not applicable for a Bundle -- raises NotImplementedError."""
        raise NotImplementedError(
            "BundleResource does not map to a single SENAITE object. "
            "Use process() or iterate getServiceRequests() instead."
        )

    def __repr__(self):
        return "<BundleResource type={!r} entries={}>".format(
            self.bundle_type, len(self._index))
