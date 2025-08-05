# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# BES.LIMS is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
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

import argparse
import errno
import json
import os
import re
import sys
from datetime import datetime
from datetime import timedelta
from time import time

import transaction
from Products.CMFCore.permissions import ModifyPortalContent
from bes.lims.scripts import setup_script_environment
from bes.lims.tamanu import api as tapi
from bes.lims.tamanu import logger
from bes.lims.tamanu.config import SAMPLE_FINAL_STATUSES
from bes.lims.tamanu.config import SENAITE_PROFILES_CODING_SYSTEM
from bes.lims.tamanu.config import SENAITE_TESTS_CODING_SYSTEM
from bes.lims.tamanu.config import SNOMED_CODING_SYSTEM
from bes.lims.tamanu.config import TAMANU_USER
from bes.lims.tamanu.session import TamanuSession
from bika.lims import api
from bika.lims.api import security as sapi
from bika.lims.utils.analysisrequest import \
    create_analysisrequest as create_sample
from bika.lims.workflow import doActionFor
from requests import ConnectionError
from senaite.core.api import dtime
from senaite.core.catalog import CLIENT_CATALOG
from senaite.core.catalog import CONTACT_CATALOG
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.decorators import retriable
from senaite.patient import api as papi

__doc__ = """
Import and sync Tamanu resources
Imports existing resources from Tamanu server and creates them in SENAITE. They
are updated accordingly if already exists in SENAITE.
"""

parser = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument(
    "-th", "--tamanu_host",
    help="URL from the Tamanu instance to extract the data from"
)
parser.add_argument(
    "-tu", "--tamanu_user",
    help="User and password in the <username>:<password> form"
)
parser.add_argument(
    "-su", "--senaite_user",
    help="SENAITE user"
)
parser.add_argument(
    "-r", "--resource",
    help="Resource type to sync. Supported: Patient, ServiceRequest"
)
parser.add_argument(
    "-s", "--since",
    help="Last updated since. Supports d (days), hours (hours), minutes (m)"
)

parser.add_argument(
    "-c", "--cache",
    help="The local filesystem path for cached content"
)

parser.add_argument(
    "-cs", "--cache_since",
    help="Default days to keep cached content since their last update date",
)

parser.add_argument(
    "-d", "--dry", action="store_true",
    help="Run in dry mode"
)

# File where sync data (e.g. last update date, etc.) will be stored
SYNC_DATA_FILE = "cache"

# Default since in dhm format
DEFAULT_SINCE = "1d"

# Default days to keep cache
DEFAULT_CACHE_SINCE = "7d"

# Username at SENAITE
USERNAME = "tamanu"

# SNOMED category for "Laboratory procedure (procedure)"
# https://browser.ihtsdotools.org/?perspective=full&conceptId1=108252007
SNOMED_REQUEST_CATEGORY = "108252007"

# Code of the location from Encounter to assign as the Ward of the Sample
WARD_CODE = "wa"

SKIP_STATUSES = (
    # Service Request statuses to skip
    "revoked", "draft", "entered-in-error", "completed"
)

TRANSITIONS = (
    # Tuples of (tamanu status, transition)
    ("revoked", "cancel"),
    ("entered-in-error", "reject"),
)

# Priorities mapping
PRIORITIES = (
    ("stat", "1"),
    ("asap", "3"),
    ("routine", "5"),
)

# Days/Hours/Minutes regex
DHM_REGEX = r'^((?P<d>(\d+))d){0,1}\s*' \
            r'((?P<h>(\d+))h){0,1}\s*' \
            r'((?P<m>(\d+))m){0,1}\s*'

_cache_path = None
_cache_since = DEFAULT_CACHE_SINCE
_cache = None


def error(message, code=1):
    """Exit with error
    """
    print("ERROR: %s" % message)
    sys.exit(code)


def conflict_error(*args, **kwargs):
    """Exits with a conflict error
    """
    error("ConflictError: exhausted retries", code=os.EX_SOFTWARE)


def connection_error(message):
    """Exits with a connection error
    """
    error("ConnectionError: %s" % message, code=os.EX_UNAVAILABLE)


def get_client(service_request):
    """Returns a client object counterpart for the given resource
    """
    resource = service_request.getServiceProvider()
    client = resource.getObject()
    if client:
        return client

    name = resource.get("name")
    if not name:
        raise ValueError("Client without name: %r" % resource)

    # search by name/title
    query = {
        "portal_type": "Client",
        "title":  name,
        "sort_on": "created",
        "sort_order": "descending",
    }
    brains = api.search(query, CLIENT_CATALOG)
    if not brains:
        container = api.get_portal().clients
        return tapi.create_object(container, resource, "Client")

    # link the resource to this Client object
    client = api.get_object(brains[0])
    tapi.link_tamanu_resource(client, resource)
    return client


def get_contact(service_request):
    """Returns a contact object counterpart for the given resource and client
    """
    # get the client
    client = get_client(service_request)
    client_uid = api.get_uid(client)

    # get the contact
    resource = service_request.getRequester()
    contact = resource.getObject()
    if contact:
        return contact

    keys = ["Firstname", "Middleinitial", "Middlename", "Surname"]
    name_info = resource.get_name_info()
    full_name = filter(None, [name_info.get(key) for key in keys])
    full_name = " ".join(full_name).strip()
    if not full_name:
        raise ValueError("Contact without name: %r" % resource)

    # search by fullname
    query = {
        "portal_type": "Contact",
        "getFullname": full_name,
        "getParentUID": client_uid,
        "sort_on": "created",
        "sort_order": "descending"
    }
    brains = api.search(query, CONTACT_CATALOG)
    if not brains:
        return tapi.create_object(client, resource, "Contact")

    # link the resource to this Contact object
    contact = api.get_object(brains[0])
    tapi.link_tamanu_resource(contact, resource)
    return contact


def get_patient(resource):
    """Returns a patient object counterpart for the given resource
    """
    patient = resource.getObject()
    if patient:
        return patient

    mrn = resource.get_mrn()
    if not mrn:
        raise ValueError("Patient without MRN (ID): %r" % resource)

    # search by mrn
    patient = papi.get_patient_by_mrn(mrn, include_inactive=True)
    if not patient:
        # Create a new patient
        container = api.get_portal().patients
        return tapi.create_object(container, resource, "Patient")

    # link the resource to this Patient object
    tapi.link_tamanu_resource(patient, resource)
    return patient


def get_sample_type(service_request):
    """Returns a sample type counterpart for the given resource
    """
    specimen = service_request.getSpecimen()
    specimen_type = specimen.get("type")
    if not specimen_type:
        return None

    sample_type = specimen.get_sample_type()
    if sample_type:
        return sample_type

    info = specimen.get_sample_type_info()
    if not info:
        return None

    # TODO QA We create the sample type if no matches are found!
    title = info.get("title")
    if not title:
        raise ValueError("Sample type without title: %s" % repr(specimen))

    setup = api.get_senaite_setup()
    container = setup.sampletypes
    return api.create(container, "SampleType", **info)


def get_sample_point(service_request):
    """Returns a sample type counterpart for the given resource if defined
    """
    specimen = service_request.getSpecimen()
    sample_point = specimen.get_sample_point()
    if sample_point:
        return sample_point

    info = specimen.get_sample_point_info()
    if not info:
        # Sample point is not a required field
        return None

    # TODO QA We create the sample point if no matches are found!
    title = info.get("title")
    if not title:
        raise ValueError("Sample point without title: %s" % repr(specimen))

    container = api.get_senaite_setup().samplepoints
    return api.create(container, "SamplePoint", **info)

def get_ward(service_request):
    """Returns a Ward object counterpart for the given resource
    """
    # TODO Remove after Ward content types are migrated to bes.lims
    if "Ward" not in api.get_portal_types():
        return None

    encounter = service_request.getEncounter()
    if not encounter:
        return None

    # get the locations from encounter that represent a Ward
    locations = encounter.getLocations(physical_type=WARD_CODE)
    if not locations:
        return None

    # TODO We pick the last location from the list of Wards here
    resource = locations[-1].get("location") or {}
    name = resource.get("display")
    if not name:
        return None

    # search by name/title
    query = {
        "portal_type": "Ward",
        "title":  name,
        "sort_on": "created",
        "sort_order": "descending",
    }
    brains = api.search(query, SETUP_CATALOG)
    if not brains:
        # create a ward
        container = api.get_setup().wards
        return api.create(container, "Ward", title=name)

    return api.get_object(brains[0])

def get_services(service_request):
    """Returns the service objects counterpart for the given resource
    """
    services = []

    # get all services and group them by title
    by_keyword = {}
    sc = api.get_tool(SETUP_CATALOG)
    for brain in sc(portal_type="AnalysisService"):
        obj = api.get_object(brain)
        by_keyword[obj.getKeyword()] = obj

    # get the codes requested in the ServiceRequest
    details = service_request.get("orderDetail")
    for coding in tapi.get_codings(details, SENAITE_TESTS_CODING_SYSTEM):
        # get the analysis by keyword
        code = coding.get("code")
        service = by_keyword.pop(code, None)
        if service:
            services.append(service)

    return services


def get_profiles(service_request):
    """Returns the profile objects counterpart for the given resource
    """
    profiles = []

    # get all profiles and group them by profile key and title
    by_title = {}
    by_keyword = {}
    sc = api.get_tool(SETUP_CATALOG)
    for brain in sc(portal_type="AnalysisProfile"):
        obj = api.get_object(brain)
        by_title[api.get_title(obj)] = obj
        key = obj.getProfileKey()
        if key:
            by_keyword[key] = obj

    # get the profile codes requested in the ServiceRequest
    codings = service_request.get("code")
    for coding in tapi.get_codings(codings, SENAITE_PROFILES_CODING_SYSTEM):
        # get the profile by keyword
        code = coding.get("code")
        profile = by_keyword.get(code)
        if not profile:
            # fallback to title
            # TODO Fallback searches by analysis to CommercialName instead?
            display = coding.get("display")
            profile = by_title.get(display)

        if profile:
            profiles.append(profile)

    return profiles


def get_remarks(service_request):
    """Returns the Remarks counterpart for the given resource
    """
    remarks = []
    notes = service_request.get("note") or []
    for note in notes:
        item = {
            "user_id": "tamanu",
            "user_name": "Tamanu",
            "created": note.get("time"),
            "content": note.get("text")
        }
        remarks.append(item)
    return remarks


def get_relevant_clinical_information(service_request):
    """Returns the relevant clinical information counterpart for the given
    resource
    """
    contents = []
    notes = service_request.get("note") or []
    for note in notes:
        text = note.get("text")
        if text:
            contents.append(text)
    return "\n".join(contents)


def get_specifications(sample_type):
    """Returns the list of specifications as brains assigned to the sample type
    """
    query = {
        "portal_type": "AnalysisSpec",
        "sampletype_uid": api.get_uid(sample_type),
        "is_active": True,
    }
    return api.search(query, SETUP_CATALOG)


def to_timedelta(since):
    """Returns a timedelta for the given
    """
    if isinstance(since, timedelta):
        return since

    if api.is_floatable(since):
        # days by default
        return timedelta(days=api.to_int(since))

    # to lowercase and remove leading and trailing spaces
    since_dhm = since.lower().strip()

    # extract the days, hours and minutes
    matches = re.search(DHM_REGEX, since_dhm)
    values = [matches.group(v) for v in "dhm"]

    # if all values are None, assume the dhm format was not valid
    nones = [value is None for value in values]
    if all(nones):
        raise ValueError("Not a valid dhm: {}".format(repr(since)))

    # replace Nones with zeros and return timedelta
    values = [api.to_int(value, 0) for value in values]
    return timedelta(days=values[0], hours=values[1], minutes=values[2])


def sync_patients(session, since):
    # get the patients created/modified since?
    since = to_timedelta(since)

    # get the resources from the remote server
    resources = session.get_resources(
        "Patient",
        all_pages=True,
        _lastUpdated=since,
        active=True,
    )

    total = len(resources)
    for num, resource in enumerate(resources):
        if num and num % 10 == 0:
            logger.info("Processing patients {}/{}".format(num, total))

        # create or update the patient counterpart at SENAITE
        sync_patient(resource)


@retriable(sync=True)
def sync_patient(resource):
    mrn = resource.get_mrn() or "unk"
    hash = "%s %s" % (mrn, resource.UID)

    # skip if up-to-date in our temp cache
    if is_up_to_date(resource):
        logger.info("Skip %s. Patient is up-to-date with cache" % hash)
        return

    logger.info("Processing Patient '{}' ({})".format(mrn, resource.UID))

    # get/create the patient
    patient = get_patient(resource)

    # update the patient
    values = resource.to_object_info()
    api.edit(patient, check_permissions=False, **values)

    # assign ownership to 'tamanu' user
    creator = patient.Creator()
    if creator != TAMANU_USER:
        sapi.revoke_local_roles_for(patient, roles=["Owner"], user=creator)

    # grant 'Owner' role to the user who is modifying the object
    sapi.grant_local_roles_for(patient, roles=["Owner"], user=TAMANU_USER)

    # don't allow the edition, but to tamanu (Owner) only
    sapi.manage_permission_for(patient, ModifyPortalContent, ["Owner"])

    # re-index object security indexes (e.g. allowedRolesAndUsers)
    patient.reindexObjectSecurity()

    # flush the object from memory
    patient._p_deactivate()

    # commit transaction
    transaction.commit()

    # store the modification date of this record in cache
    cache_modified(resource)


def sync_service_requests(session, since):
    # get the service requests created/modified since?
    since = to_timedelta(since)
    # only interested on non-image request categories
    category = "%s|%s" % (SNOMED_CODING_SYSTEM, SNOMED_REQUEST_CATEGORY)

    # get the resources from the remote server
    resources = session.get_resources(
        "ServiceRequest",
        all_pages=True,
        _lastUpdated=since,
        category=category
    )

    total = len(resources)
    logger.info("Processing %s service requests ..." % total)
    for num, sr in enumerate(resources):
        if num and num % 10 == 0:
            logger.info("Processing service requests %s/%s" % (num, total))

        # create or update the service request counterpart at SENAITE
        try:
            sync_service_request(sr)
        except Exception as e:
            hash = "%s %s" % (sr.getLabTestID(), sr.UID)
            try:
                data = json.dumps(sr.to_dict())
            except Exception:
                data = "-- invalid json ---"
            logger.error("Error while importing %s:\n%s\n" % (hash, data))
            raise


@retriable(sync=True, on_retry_exhausted=conflict_error)
def sync_service_request(sr):
    # get the Tamanu's test ID for this ServiceRequest
    tid = sr.getLabTestID()
    hash = "%s %s" % (tid, sr.UID)

    # skip if up-to-date in our temp cache
    if is_up_to_date(sr):
        logger.info("Skip %s. Sample is up-to-date with cache" % hash)
        return

    # skip if the category is not supported
    category = sr.get("category")
    codes = tapi.get_codes(category, SNOMED_CODING_SYSTEM)
    if SNOMED_REQUEST_CATEGORY not in codes:
        logger.info("Skip %s. Category is not supported" % hash)
        return

    # get SampleType, Site and DateSampled via FHIR's specimen
    specimen = sr.getSpecimen()
    if not specimen:
        logger.info("Skip %s. Specimen is missing" % hash)
        return

    # the fullname of the practitioner who collected the sample
    collector = specimen.getCollectorName()

    # get the sample type
    sample_type = get_sample_type(sr)
    if not sample_type:
        logger.info("Skip %s. Sample type is missing" % hash)
        return

    # get the sample for this ServiceRequest, if any
    sample = sr.getObject()

    # skip if sample does not exist yet and no valid status
    if not sample and sr.status in SKIP_STATUSES:
        logger.info("Skip %s. Status is not valid: %s" % (hash, sr.status))
        return

    # skip if sample is up-to-date
    tamanu_modified = tapi.get_tamanu_modified(sr)
    sample_modified = tapi.get_tamanu_modified(sample)
    if sample and tamanu_modified <= sample_modified:
        logger.info("Skip %s. Sample is up-to-date: %r" % (hash, sample))
        return

    # skip if the sample cannot be edited
    if sample and api.get_review_status(sample) in SAMPLE_FINAL_STATUSES:
        msg = "Skip %s. Sample cannot be edited: %r" % (hash, sample)
        logger.info(msg)
        # store the modification date of this record in cache
        cache_modified(sr)
        return

    # get the specification if only assigned to this sample type
    specs = get_specifications(sample_type)
    spec = api.get_object(specs[0]) if len(specs) == 1 else None

    # get the sample point
    sample_point = get_sample_point(sr)
    sample_point_uid = api.get_uid(sample_point) if sample_point else None

    # date sampled
    date_sampled = specimen.get_date_sampled()

    # get the priority
    priority = sr.get("priority")
    priority = dict(PRIORITIES).get(priority, "5")

    # get the remarks (notes)
    #remarks = get_remarks(sr)

    # get the relevant clinical info (notes)
    clinical_info = get_relevant_clinical_information(sr)

    # get or create the client via FHIR's encounter/serviceProvider
    client = get_client(sr)

    # get or create the contact via FHIR's requester
    contact = get_contact(sr)

    # get or create the patient via FHIR's subject
    patient_resource = sr.getPatientResource()
    patient = get_patient(patient_resource)
    patient_mrn = patient.getMRN()
    patient_dob = patient.getBirthdate()
    patient_sex = patient.getSex()
    patient_name = {
        "firstname": patient.getFirstname(),
        "middlename": patient.getMiddlename(),
        "lastname": patient.getLastname(),
    }

    # get or create the ward via Encounter locations
    ward = get_ward(sr)

    # get profiles
    profiles = get_profiles(sr)
    profiles = map(api.get_uid, profiles)

    # get the services
    services = get_services(sr)

    # create the sample
    values = {
        "Client": client,
        "Contact": contact,
        "SampleType": sample_type,
        "SamplePoint": sample_point,
        "Site": sample_point_uid,
        "DateSampled": date_sampled,
        "Profiles": profiles,
        "MedicalRecordNumber": {"value": patient_mrn},
        "PatientFullName": patient_name,
        "DateOfBirth": patient_dob,
        "Sex": patient_sex,
        "Priority": priority,
        "ClientSampleID": tid,
        "Collector": collector,
        "Sampler": collector,
        #"Remarks": remarks,
        "Specification": spec,
        "Ward": ward,
        "ClinicalInformation": clinical_info,
        #"DateOfAdmission": doa,
        #"CurrentAntibiotics": antibiotics,
        #"Volume": volume,
        # TODO WardDepartment: sr.get("encounter").get("location")?
        #"WardDepartment": department,
        #"Location": dict(LOCATIONS).get("location", ""),
    }
    request = api.get_request() or api.get_test_request()
    if sample:
        # edit sample
        edit_sample(sample, **values)
        logger.info("Edited: %s %r" % (hash, sample))
    else:
        # create the sample
        sample = create_sample(client, request, values, services)
        logger.info("Created: %s %r" % (hash, sample))

    # link the tamanu resource to this sample
    tapi.link_tamanu_resource(sample, sr)

    # do the transition
    action = dict(TRANSITIONS).get(sr.status)
    if action:
        doActionFor(sample, action)
        logger.info("Action (%s): %s %r" % (action, hash, sample))

    # commit transaction
    transaction.commit()

    # store the modification date of this record in cache
    cache_modified(sr)


def edit_sample(sample, **kwargs):
    # pop non-editable fields
    fields = api.get_fields(sample)
    for field_name, field in fields.items():
        # cannot update readonly fields
        readonly = getattr(field, "readonly", False)
        if readonly:
            kwargs.pop(field_name, None)

        # check field writable permission
        perm = getattr(field, "write_permission", ModifyPortalContent)
        if perm and not sapi.check_permission(perm, sample):
            kwargs.pop(field_name, None)

    # edit the sample
    api.edit(sample, **kwargs)


def get_cache_file():
    """Returns the file for caching
    """
    global _cache_path
    if not _cache_path:
        return None

    filename = os.path.join(_cache_path, SYNC_DATA_FILE)
    if not os.path.exists(os.path.dirname(filename)):
        try:
            os.makedirs(os.path.dirname(filename))
        except OSError as exc:  # Guard against race condition
            if exc.errno != errno.EEXIST:
                raise
    return filename


def get_cache():
    """Get the data of resources synchronization stored in a local file
    """
    global _cache
    if not _cache:
        cache_file = get_cache_file()
        if not cache_file:
            return {}
        if not os.path.isfile(cache_file):
            return {}

        # read from the file and convert to a dict
        with open(cache_file, "r") as in_file:
            data = in_file.read()
        _cache = api.parse_json(data, {})

    return _cache


def set_cache(data):
    """Store synchronization information in a local file
    """
    # filter records before the cache since
    if _cache_since:
        since = to_timedelta(_cache_since)
        min_date = dtime.to_ansi(datetime.now() - since)
        n_data = {}
        for key, val in data.items():
            if val > min_date:
                n_data[key] = val
        json_data = json.dumps(n_data)
    else:
        json_data = json.dumps(data)
    cache_file = get_cache_file()
    if cache_file:
        with open(cache_file, "w") as out_file:
            out_file.write(json_data)

    # reset the cache
    global _cache
    _cache = data


def cache_modified(resource):
    # get the modification date of the tamanu resource
    uid = resource.UID
    modified = dtime.to_ansi(resource.modified)
    if not modified:
        return

    # store the modification time of this resource
    data = get_cache()
    data[uid] = modified
    set_cache(data)


def is_up_to_date(resource):
    # get the modification date of the tamanu resource
    uid = resource.UID
    modified = dtime.to_ansi(resource.modified)
    if not modified:
        # maybe created??
        return False

    # get the modification date time we keep in our cache
    data = get_cache()
    last_modified = data.get(uid)
    last_modified = dtime.to_dt(last_modified)
    last_modified = dtime.to_ansi(last_modified)
    if not last_modified:
        return False

    return modified <= last_modified


def main(app):
    global _cache_path
    args, _ = parser.parse_known_args()
    if hasattr(args, "help") and args.help:
        print("")
        parser.print_help()
        parser.exit()
        return

    # get the remote host
    host = args.tamanu_host
    if not host:
        error("Remote URL is missing")

    # get the local filesystem path for cached content
    _cache_path = args.cache

    # get the user and password
    try:
        user, password = args.tamanu_user.split(":")
    except (AttributeError, ValueError):
        error("Credentials are missing or not valid format")
        return

    # get since dhms
    since = args.since or DEFAULT_SINCE

    # get cache since dhms
    _cache_since = args.cache_since or DEFAULT_CACHE_SINCE

    # mapping of supported resource types and sync functions
    resources = {
        "Patient": sync_patients,
        "ServiceRequest": sync_service_requests
    }

    # get the resource type to synchronize
    sync_func = resources.get(args.resource)
    if not sync_func:
        error("Resource type is missing or not valid")

    # Setup environment
    username = args.senaite_user or USERNAME
    setup_script_environment(app, username=username, logger=logger)

    # do the work
    logger.info("-" * 79)
    logger.info("Synchronizing with %s ..." % host)
    if _cache_path:
        logger.info("Cache path: {}".format(_cache_path))
        logger.info("Cache since: {}".format(_cache_since))
    logger.info("Started: {}".format(datetime.now().isoformat()))
    start = time()

    # Start a session with Tamanu server
    session = TamanuSession(host)
    logged = session.login(user, password)
    if not logged:
        error("Cannot login, wrong credentials")

    try:
        # Call the sync function
        sync_func(session, since)
    except ConnectionError as e:
        connection_error(str(e))

    if args.dry:
        # Dry mode. Do not do transaction
        print("Dry mode. No changes done")
        return

    # Commit transaction
    transaction.commit()
    logger.info("Synchronizing with %s [DONE]" % host)
    logger.info("Elapsed: {}".format(timedelta(seconds=(time() - start))))
    logger.info("-" * 79)


if __name__ == "__main__":
    main(app)  # noqa: F821
