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

from bika.lims import api
from bes.lims.tamanu import logger
from bes.lims.tamanu.config import TAMANU_STORAGE
from bes.lims.tamanu.interfaces import ITamanuContent
from bes.lims.tamanu.interfaces import ITamanuResource
from persistent.dict import PersistentDict
from Products.Archetypes.utils import getRelURL
from senaite.core.api import dtime
from uuid import UUID
from zope.annotation.interfaces import IAnnotations
from zope.interface import alsoProvides

_marker = object

UID_CATALOG = "uid_catalog"


def is_tamanu_content(obj):
    """Returns whether the object passed has a counterpart content at Tamanu
    """
    return ITamanuContent.providedBy(obj)


def is_tamanu_resource(obj):
    """Returns whether the object passed in is a Tamanu's HL7 resource
    """
    return ITamanuResource.providedBy(obj)


def get_tamanu_storage(obj):
    """Get or creates the Tamanu storage for the given object

    :param obj: Content object
    :returns: PersistentDict
    """
    annotation = IAnnotations(obj)
    if annotation.get(TAMANU_STORAGE) is None:
        annotation[TAMANU_STORAGE] = PersistentDict()
    return annotation[TAMANU_STORAGE]


def get_tamanu_uid(obj):
    """Returns the UID of the counterpart content at Tamanu, if any
    """
    if is_tamanu_resource(obj):
        return obj.UID
    if is_tamanu_content(obj):
        storage = get_tamanu_storage(obj)
        return storage.get("uid", None)
    return None


def get_tamanu_host(obj):
    """Returns the host where the counterpart Tamanu content is located
    """
    if is_tamanu_resource(obj):
        return obj.session.host
    if is_tamanu_content(obj):
        storage = get_tamanu_storage(obj)
        return storage.get("host", None)
    return None


def get_tamanu_modified(obj):
    """Returns the datetime when the obj was modified at Tamanu
    """
    modified = None
    if is_tamanu_resource(obj):
        meta = obj.get("meta") or {}
        modified = meta.get("lastUpdated")
    if is_tamanu_content(obj):
        storage = get_tamanu_storage(obj)
        data = storage.get("data")
        meta = data.get("meta") or {}
        modified = meta.get("lastUpdated")
    return dtime.to_dt(modified)


def get_tamanu_session(host, email, password):
    """Returns a TamanuSession for the given host
    """
    from bes.lims.tamanu.session import TamanuSession
    session = TamanuSession(host)
    session.login(email, password)
    return session


def get_tamanu_session_for(obj):
    """Returns a Tamanu Session for the given object
    """
    # TODO Use a singleton utility to get tamanu session
    if is_tamanu_resource(obj):
        return obj.session
    if is_tamanu_content(obj):
        host = get_tamanu_host(obj)
        if not host:
            raise ValueError("Tamanu content, but no host: %s" % repr(obj))

        # get the creds
        storage = get_tamanu_storage(obj)
        email, password = storage.get("auth")

        # create the session
        return get_tamanu_session(host, email, password)

    return None


def get_brain_by_tamanu_uid(uid, default=None):
    """Query a brain by a given Tamanu UID
    """
    if not uid:
        return default

    uc = api.get_tool(api.UID_CATALOG)
    brains = uc(tamanu_uid=uid)
    if len(brains) != 1:
        return default
    return brains[0]


def get_object_by_tamanu_uid(uid, default=_marker):
    """Returns the object for the given Tamanu UID

    :param uid: The Tamanu UID to search by
    :type uid: string
    :returns: Found Object or default
    """
    if not uid:
        if default is not _marker:
            return default
        raise ValueError("uid not set")

    brain = get_brain_by_tamanu_uid(uid)
    if not brain:
        if default is not _marker:
            return default
        raise ValueError("No object found for tamanu_uid {}".format(uid))

    return api.get_object(brain)


def get_uuid(thing):
    """Returns an uuid.UUID object
    """
    if isinstance(thing, UUID):
        return thing
    if is_tamanu_resource(thing):
        return UUID(thing.UID)
    uid = api.get_uid(thing)
    if thing == "0":
        raise ValueError("Not a valid UID: %s" % repr(thing))
    return UUID(uid)


def get_object(thing, default=_marker):
    """Get the full content object
    """
    if is_tamanu_resource(thing):
        return get_object_by_tamanu_uid(thing.UID, default=default)

    # rely on core's api
    if default is _marker:
        return api.get_object(thing)

    return api.get_object(thing, default=default)


def get_status(thing):
    """Gets the state of a resource or the review state of a SENAITE object
    """
    if is_tamanu_resource(thing):
        return thing.get_raw("status")
    return api.get_review_status(thing)


def create_object(container, resource, portal_type, **kwargs):
    """Creates an object for the given Tamanu resource
    """
    if not is_tamanu_resource(resource):
        raise ValueError("Type not supported: {}".format(repr(type(resource))))

    # check if the object exists already!
    tamanu_uid = resource.UID
    brain = get_brain_by_tamanu_uid(tamanu_uid)
    if brain:
        raise ValueError("An object with Tamanu's UID {} exists already"
                         .format(tamanu_uid))

    # get the data from the resource
    info = resource.to_object_info()
    info.update(kwargs)

    # get the container
    container = api.get_object(container)

    # remove portal_type from info
    info.pop("portal_type", None)

    # create the object
    obj = api.create(container, portal_type, **info)
    logger.info("Object created: %s" % repr(obj))

    # link the tamanu resource to this object
    link_tamanu_resource(obj, resource)
    return obj


def link_tamanu_resource(obj, resource):
    """Assigns the tamanu uid to the given object
    """
    if not is_tamanu_resource(resource):
        raise ValueError("Type not supported: {}".format(repr(type(resource))))

    # mark the object with ITamanuContent, so we can always know before hand
    # if this object has a counterpart resource at Tamanu
    alsoProvides(obj, ITamanuContent)

    # assign the tamanu uid, along with current data so we can always use
    # the original information, even when connection with Tamanu is lost
    annotation = get_tamanu_storage(obj)
    annotation["uid"] = resource.UID
    annotation["data"] = resource.to_dict()
    annotation["host"] = resource.session.host
    # TODO Rely on an utility instead of storing auth creds
    annotation["auth"] = resource.session._auth

    # index tamanu_uid from uid_catalog
    catalog_object(obj)


def catalog_object(obj):
    """Catalog the object in all registered catalogs
    """
    uid_catalog = api.get_tool(UID_CATALOG)
    if api.is_at_content(obj):
        # For ATs, the uids of uid_catalog are relative paths to portal root
        # see Products.Archetypes.UIDCatalog.UIDResolver.catalog_object
        url = getRelURL(uid_catalog, obj.getPhysicalPath())
    else:
        # For DXs, the uids of uid_catalog are absolute paths to portal root
        # see plone.app.referencablebehavior.uidcatalog
        url = "/".join(obj.getPhysicalPath())

    # explicitly catalog in uid_catalog
    uid_catalog.catalog_object(obj, url)

    # reindex in registered catalogs
    obj.reindexObject()


def get_codings(items, system):
    """Return the codes from a list of a dicts for the system specified
    """
    if not items:
        return []
    if not isinstance(items, list):
        items = [items]
    codings = []
    for item in items:
        coding = item.get("coding") or []
        for code in coding:
            if code.get("system") != system:
                continue
            codings.append(code)
    return codings


def get_codes(items, system):
    """Return the codes from a list of dicts for the system specified
    """
    codings = get_codings(items, system)
    return [coding.get("code") for coding in codings]
