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

import json
from datetime import datetime
from datetime import timedelta

import requests
from bes.lims.tamanu import logger
from bes.lims.tamanu.interfaces import ITamanuResource
from bes.lims.tamanu.resources import TamanuResource
from zope.component import queryAdapter

# endpoint-specific slugs
SLUGS = (
    ("login", "v1"),
)

# default slug
DEFAULT_SLUG = "v1/integration/fhir/mat"

# basic headers
HEADERS = (
    ("X-Version", "0.0.1"),
    ("X-Tamanu-Client", "mSupply"),
    ("Content-Type", "application/json"),
)


class TamanuSession(object):

    token = "unk"
    _auth = None

    def __init__(self, host):
        self.host = host

    def login(self, email, password):
        # TODO remove _auth
        self._auth = (email, password)
        auth = dict(email=email, password=password)
        resp = self.post("login", payload=auth)
        self.token = resp.json().get("token")
        if self.token:
            return True
        return False

    def get_slug(self, endpoint):
        slug = dict(SLUGS).get(endpoint)
        if slug:
            return slug
        return DEFAULT_SLUG

    def get_url(self, endpoint):
        """Returns the url of the remote instance and endpoint
        """
        if self.host not in endpoint:
            slug = self.get_slug(endpoint)
            parts = filter(None, [self.host, slug, endpoint])
            endpoint = "/".join(parts)
        return endpoint

    def post(self, endpoint, payload, **kwargs):
        url = self.get_url(endpoint)

        # add the default headers
        headers = kwargs.pop("headers", {})
        headers.update(dict(HEADERS))

        # inject the auth token
        if self.token:
            headers["Authorization"] = "Bearer {}".format(self.token)

        kwargs["headers"] = headers

        # Send the POST request
        logger.info("[POST] {}".format(url))
        logger.info("[POST PAYLOAD] {}".format(repr(payload)))
        resp = requests.post(url, data=json.dumps(payload), **kwargs)
        code = resp.status_code
        if code not in [200, 201]:
            logger.error("[ERROR {}]: {}".format(str(code), resp.content))

        # Return the response
        return resp

    def get(self, endpoint, params=None, **kwargs):
        url = self.get_url(endpoint)

        # add the default headers
        headers = kwargs.pop("headers", {})
        headers.update(dict(HEADERS))

        # inject the auth token
        headers["Authorization"] = "Bearer {}".format(self.token)
        kwargs["headers"] = headers

        # do the GET request
        logger.info("[GET] {} (params={})".format(url, repr(params)))
        resp = requests.get(url, params=params, **kwargs)

        # return the response
        return resp.json() or {}

    def get_resource_by_uid(self, resource_type, uid):
        endpoint = "{}/{}".format(resource_type, uid)
        item = self.get(endpoint)
        return self.to_resource(item)

    def to_resource(self, item):
        """Converts the item to a Tamanu resource of suitable type
        """
        if not item:
            return None

        # items without these keys are not supported
        required = ["resourceType", "id"]
        for key in required:
            if not item.get(key, False):
                logger.error("Cannot get resource: %s is empty" % key)
                return None

        # Look-up the proper type by using named adapters, where the name
        # is the value for 'resourceType' name
        resource_type = item.get("resourceType")
        name = "tamanu.resource.{}".format(resource_type)
        resource = queryAdapter(self, ITamanuResource, name)
        if resource:
            return resource.wrap(item)

        # Fall-back to default
        return TamanuResource(self, data=item)

    def get_resources(self, resource_type, all_pages=False, **kwargs):
        # minimum criteria for the payload
        payload = {
            "_page": 0,
            "_count": 1000,
        }
        payload.update(kwargs)

        # calculates since time
        last_updated = payload.pop("_lastUpdated", None)
        if isinstance(last_updated, timedelta):
            last_updated = datetime.now() - last_updated

        if isinstance(last_updated, datetime):
            last_updated = last_updated.strftime("%Y-%m-%dT%H:%M:%S")
            payload["_lastUpdated"] = "gt{}".format(last_updated)

        # get the raw data in json format
        records = []
        while True:
            data = self.get(resource_type, params=payload)

            # entries are a list of dicts under 'entry'
            entries = data.get("entry", [])
            records.extend(entries)

            # no more pages needed
            if not all_pages or len(entries) < payload.get("_count"):
                break

            # increase in one page
            payload["_page"] += 1

        # each entry has the resource itself under 'resource'
        items = map(lambda record: record.get("resource"), records)

        # return the proper resource types
        resources = map(self.to_resource, items)
        return filter(None, resources)
