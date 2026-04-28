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

"""Doctests for BundleResource.

These tests cover BundleResource in isolation -- no Zope, no SENAITE catalog,
no HTTP. The only dependencies are the resource wrapper classes themselves.

Run with:
    python -m doctest test_bundle.py -v

Or via zope.testrunner:
    bin/test -s bes.lims -t test_bundle
"""

import doctest
import unittest

# ---------------------------------------------------------------------------
# Minimal Bundle fixture
#
# One of each resource type, using urn:uuid fullUrls and matching UUIDs as
# resource ids -- consistent with the real Bundle format.
# ---------------------------------------------------------------------------

BUNDLE = {
    "resourceType": "Bundle",
    "id": "TestBundle",
    "type": "transaction",
    "entry": [
        {
            "fullUrl": "urn:uuid:aaaa0001-0000-0000-0000-000000000000",
            "resource": {
                "resourceType": "Patient",
                "id": "aaaa0001-0000-0000-0000-000000000000",
                "identifier": [{"value": "MRN-001"}],
                "name": [{"family": "Smith", "given": ["Alice", "M"]}],
                "gender": "female",
                "birthDate": "1990-06-15",
            }
        },
        {
            "fullUrl": "urn:uuid:bbbb0002-0000-0000-0000-000000000000",
            "resource": {
                "resourceType": "Organization",
                "id": "bbbb0002-0000-0000-0000-000000000000",
                "identifier": [{"value": "ORG-001"}],
                "name": "City Hospital",
            }
        },
        {
            "fullUrl": "urn:uuid:cccc0003-0000-0000-0000-000000000000",
            "resource": {
                "resourceType": "Practitioner",
                "id": "cccc0003-0000-0000-0000-000000000000",
                "identifier": [{"value": "PRACT-001"}],
                "name": [{"family": "Jones", "given": ["Bob"]}],
            }
        },
        {
            "fullUrl": "urn:uuid:dddd0004-0000-0000-0000-000000000000",
            "resource": {
                "resourceType": "Location",
                "id": "dddd0004-0000-0000-0000-000000000000",
                "name": "City Hospital - Ward A",
            }
        },
        {
            "fullUrl": "urn:uuid:eeee0005-0000-0000-0000-000000000000",
            "resource": {
                "resourceType": "Encounter",
                "id": "eeee0005-0000-0000-0000-000000000000",
                "status": "completed",
                "serviceProvider": {
                    "reference": "urn:uuid:bbbb0002-0000-0000-0000-000000000000"
                },
                "location": [{
                    "location": {
                        "reference": "urn:uuid:dddd0004-0000-0000-0000-000000000000",
                        "display": "City Hospital - Ward A",
                    },
                    "form": {
                        "coding": [{
                            "system": "http://terminology.hl7.org/CodeSystem/location-physical-type",
                            "code": "wa",
                            "display": "Ward",
                        }]
                    }
                }]
            }
        },
        {
            "fullUrl": "urn:uuid:ffff0006-0000-0000-0000-000000000000",
            "resource": {
                "resourceType": "Specimen",
                "id": "ffff0006-0000-0000-0000-000000000000",
                "type": {
                    "coding": [{
                        "system": "http://snomed.info/sct",
                        "code": "119364003",
                        "display": "Serum specimen",
                    }]
                },
                "collection": {
                    "collectedDateTime": "2026-04-08T08:30:00+10:00"
                }
            }
        },
        {
            "fullUrl": "urn:uuid:9999000a-0000-0000-0000-000000000000",
            "resource": {
                "resourceType": "ServiceRequest",
                "id": "9999000a-0000-0000-0000-000000000000",
                "status": "active",
                "intent": "order",
                "priority": "routine",
                "subject": {
                    "reference": "urn:uuid:aaaa0001-0000-0000-0000-000000000000"
                },
                "encounter": {
                    "reference": "urn:uuid:eeee0005-0000-0000-0000-000000000000"
                },
                "requester": {
                    "reference": "urn:uuid:cccc0003-0000-0000-0000-000000000000",
                    "type": "Practitioner",
                },
                "specimen": [{
                    "reference": "urn:uuid:ffff0006-0000-0000-0000-000000000000"
                }],
                "orderDetail": [{
                    "parameter": [{
                        "code": {
                            "coding": [{
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationValue",
                                "code": "LOINC",
                                "display": "Test Code",
                            }]
                        },
                        "valueCodeableConcept": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "1742-6",
                                "display": "ALT",
                            }]
                        }
                    }]
                }]
            }
        },
    ]
}


def make_bundle():
    """Return a fresh BundleResource from the test fixture."""
    from bes.lims.tamanu.resources.bundle import BundleResource
    return BundleResource(BUNDLE)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_bundle_type():
    """BundleResource exposes the bundle type.

    >>> bundle = make_bundle()
    >>> bundle.bundle_type
    'transaction'
    """


def test_bundle_repr():
    """BundleResource repr includes type and entry count.

    >>> bundle = make_bundle()
    >>> repr(bundle)
    "<BundleResource type='transaction' entries=14>"
    """


def test_get_all_no_duplicates():
    """get_all() returns each resource exactly once.

    Each entry is indexed twice (fullUrl + ResourceType/id) but should only
    appear once in get_all() results.

    >>> bundle = make_bundle()
    >>> len(bundle.getPatients())
    1
    >>> len(bundle.getOrganizations())
    1
    >>> len(bundle.getPractitioners())
    1
    >>> len(bundle.getSpecimens())
    1
    >>> len(bundle.getEncounters())
    1
    >>> len(bundle.getServiceRequests())
    1
    """


def test_resolve_by_full_url():
    """BundleResource.get() resolves a urn:uuid reference.

    >>> bundle = make_bundle()
    >>> raw = bundle.get("urn:uuid:aaaa0001-0000-0000-0000-000000000000")
    >>> raw["resourceType"]
    'Patient'
    >>> raw["id"]
    'aaaa0001-0000-0000-0000-000000000000'
    """


def test_resolve_by_resource_type_id():
    """BundleResource.get() resolves a ResourceType/id reference.

    >>> bundle = make_bundle()
    >>> raw = bundle.get("Organization/bbbb0002-0000-0000-0000-000000000000")
    >>> raw["name"]
    'City Hospital'
    """


def test_resolve_unknown_reference_returns_none():
    """BundleResource.get() returns None for an unknown reference.

    >>> bundle = make_bundle()
    >>> bundle.get("Patient/does-not-exist") is None
    True
    """


def test_to_resource_wraps_correct_class():
    """to_resource() wraps each resourceType in the right class.

    >>> from bes.lims.tamanu.resources.patient import PatientResource
    >>> from bes.lims.tamanu.resources.organization import Organization
    >>> from bes.lims.tamanu.resources.encounter import Encounter
    >>> bundle = make_bundle()
    >>> isinstance(bundle.getPatients()[0], PatientResource)
    True
    >>> isinstance(bundle.getOrganizations()[0], Organization)
    True
    >>> isinstance(bundle.getEncounters()[0], Encounter)
    True
    """


def test_to_resource_unknown_type_falls_back():
    """to_resource() falls back to TamanuResource for unknown resourceTypes.

    >>> from bes.lims.tamanu.resources import TamanuResource
    >>> bundle = make_bundle()
    >>> unknown = bundle.to_resource({"resourceType": "Foo", "id": "x"})
    >>> type(unknown).__name__
    'TamanuResource'
    """


def test_service_request_resolves_patient():
    """ServiceRequest.getPatientResource() traverses the bundle index.

    >>> bundle = make_bundle()
    >>> sr = bundle.getServiceRequests()[0]
    >>> patient = sr.getPatientResource()
    >>> patient is not None
    True
    >>> patient.UID
    'aaaa0001-0000-0000-0000-000000000000'
    """


def test_service_request_resolves_encounter():
    """ServiceRequest.getEncounter() traverses the bundle index.

    >>> bundle = make_bundle()
    >>> sr = bundle.getServiceRequests()[0]
    >>> encounter = sr.getEncounter()
    >>> encounter is not None
    True
    >>> encounter.UID
    'eeee0005-0000-0000-0000-000000000000'
    """


def test_service_request_resolves_organization_via_encounter():
    """ServiceRequest.getServiceProvider() chains through Encounter.

    >>> bundle = make_bundle()
    >>> sr = bundle.getServiceRequests()[0]
    >>> org = sr.getServiceProvider()
    >>> org is not None
    True
    >>> org.get_raw("name")
    'City Hospital'
    """


def test_service_request_resolves_specimen():
    """ServiceRequest.getSpecimen() traverses the bundle index.

    >>> bundle = make_bundle()
    >>> sr = bundle.getServiceRequests()[0]
    >>> specimen = sr.getSpecimen()
    >>> specimen is not None
    True
    >>> specimen.get_date_sampled()
    '2026-04-08T08:30:00+10:00'
    """


def test_service_request_resolves_requester():
    """ServiceRequest.getRequester() traverses the bundle index.

    >>> bundle = make_bundle()
    >>> sr = bundle.getServiceRequests()[0]
    >>> requester = sr.getRequester()
    >>> requester is not None
    True
    >>> requester.UID
    'cccc0003-0000-0000-0000-000000000000'
    """


def test_encounter_get_locations_unfiltered():
    """Encounter.getLocations() returns all locations when no form given.

    >>> bundle = make_bundle()
    >>> encounter = bundle.getEncounters()[0]
    >>> locations = encounter.getLocations()
    >>> len(locations)
    1
    """


def test_encounter_get_locations_filtered_by_ward():
    """Encounter.getLocations(form='wa') returns only ward locations.

    >>> bundle = make_bundle()
    >>> encounter = bundle.getEncounters()[0]
    >>> wards = encounter.getLocations(form="wa")
    >>> len(wards)
    1
    >>> wards[0]["location"]["display"]
    'City Hospital - Ward A'
    """


def test_encounter_get_locations_filtered_no_match():
    """Encounter.getLocations() returns empty list when form code not present.

    >>> bundle = make_bundle()
    >>> encounter = bundle.getEncounters()[0]
    >>> encounter.getLocations(form="ho")
    []
    """


def test_encounter_get_service_provider():
    """Encounter.getServiceProvider() resolves the Organization.

    >>> bundle = make_bundle()
    >>> encounter = bundle.getEncounters()[0]
    >>> org = encounter.getServiceProvider()
    >>> org is not None
    True
    >>> org.get_raw("name")
    'City Hospital'
    """


def test_process_calls_processor_once_per_resource():
    """BundleResource.process() calls the processor exactly once per resource.

    >>> bundle = make_bundle()
    >>> calls = []
    >>> def recorder(resource, **kwargs):
    ...     calls.append((resource.UID, kwargs))
    >>> ok, errors = bundle.process("ServiceRequest", recorder, dry_run=True)
    >>> ok
    1
    >>> errors
    0
    >>> len(calls)
    1
    >>> calls[0][1]
    {'dry_run': True}
    """


def test_process_catches_processor_errors():
    """BundleResource.process() catches exceptions and counts them as errors.

    >>> bundle = make_bundle()
    >>> def boom(resource, **kwargs):
    ...     raise ValueError("something went wrong")
    >>> ok, errors = bundle.process("ServiceRequest", boom)
    >>> ok
    0
    >>> errors
    1
    """


def test_process_no_matching_resources():
    """BundleResource.process() returns (0, 0) when no resources match.

    >>> bundle = make_bundle()
    >>> ok, errors = bundle.process("Observation", lambda r: None)
    >>> (ok, errors)
    (0, 0)
    """


def test_to_object_info_raises():
    """BundleResource.to_object_info() raises NotImplementedError.

    >>> bundle = make_bundle()
    >>> bundle.to_object_info()
    Traceback (most recent call last):
        ...
    NotImplementedError: ...
    """


# ---------------------------------------------------------------------------
# Test suite wiring for zope.testrunner
# ---------------------------------------------------------------------------

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(doctest.DocTestSuite(
        __name__,
        optionflags=(
            doctest.ELLIPSIS |
            doctest.NORMALIZE_WHITESPACE
        ),
    ))
    return suite


if __name__ == "__main__":
    # Allow running directly: python test_bundle.py
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(test_suite())
