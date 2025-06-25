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

import copy
from senaite.core.api import dtime
from bes.lims.tamanu.api import get_object_by_tamanu_uid
from bes.lims.tamanu import logger
from bes.lims.tamanu.interfaces import ITamanuResource
from zope.interface import implementer


_marker = object()


@implementer(ITamanuResource)
class TamanuResource(object):

    _refs = {}

    def __init__(self, session, data=None):
        self._session = session
        self._data = data or {}

    def wrap(self, data):
        self._data = data
        return self

    @property
    def session(self):
        return self._session

    @property
    def UID(self):
        """Returns the Tamanu UID of this resource
        Mimics the behavior of DX and AT types
        """
        return self.get_raw("id")

    @property
    def modified(self):
        """Returns the last modification date of this resource
        Mimics te behavior of DX and AT types
        """
        meta = self.get_raw("meta") or {}
        last_updated = meta.get("lastUpdated", None)
        return dtime.to_dt(last_updated)

    @property
    def status(self):
        """Returns the status of this resource
        """
        return self.get_raw("status")

    def getObject(self):
        """Returns the counterpart SENAITE object of this Tamanu resource
        Mimics the behavior of DX and AT types
        """
        return get_object_by_tamanu_uid(self.UID, default=None)

    def get_identifiers(self):
        """Returns a dict of {identifier_type:identifier_value}
        """
        identifiers = {}
        items = self.get_raw("identifier") or []
        for item in items:
            identifiers[item.get("system")] = item.get("value")
        return identifiers

    def to_dict(self):
        """Returns a dict representation of this object
        """
        return copy.deepcopy(self._data)

    def get_raw(self, field_name, default=None):
        return self._data.get(field_name, default)

    def is_reference(self, record):
        if not isinstance(record, dict):
            return False
        reference_id = record.get("reference")
        if reference_id:
            return True
        return False

    def get_reference(self, record_or_id):
        if isinstance(record_or_id, dict):
            ref_id = record_or_id.get("reference")
        else:
            ref_id = record_or_id
        reference = self._refs.get(ref_id)
        if not reference:
            item = self._session.get(ref_id)
            reference = self._session.to_resource(item)
            if not reference:
                logger.error("Cannot resolve reference for {}"
                             .format(repr(record_or_id)))
                return None
            self._refs[ref_id] = reference
        return self._refs[ref_id]

    def get(self, field_name, default=None):
        # is there any converter for this specific field
        func = getattr(self, "_get_{}".format(field_name), None)
        if func and callable(func):
            return func()

        record = self.get_raw(field_name, _marker)
        if record is _marker:
            return default

        # is this record a reference
        if self.is_reference(record):
            return self.get_reference(record)

        return record

    def to_object_info(self):
        """Returns a dict with the necessary information for the creation of
        an object counterpart at senaite
        """
        raise NotImplementedError("To be implemented by subclass")

    def __repr__(self):
        return repr(self._data)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()
