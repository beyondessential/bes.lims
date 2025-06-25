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

from bes.lims.tamanu import logger
from bes.lims.tamanu.resources import TamanuResource


LAB_TEST = "http://data-dictionary.tamanu-fiji.org/tamanu-mrid-labrequest.html"


class ServiceRequest(TamanuResource):
    """Object that represents a ServiceRequest resource from Tamanu
    """

    def getPatientResource(self):
        """Returns the Patient resource assigned to this ServiceRequest, if any
        """
        return self.get("subject")

    def getSpecimen(self):
        """Returns the Specimen resource assigned to this ServiceRequest
        """
        specimens = self.get("specimen")
        if not specimens:
            return None
        if len(specimens) > 1:
            # TODO only one specimen per service request is supported
            logger.error("More than one specimen: %s" % repr(specimens))
            return None
        return self.get_reference(specimens[0])

    def getEncounter(self):
        """Returns the Encounter resource assigned to this ServiceRequest
        """
        return self.get("encounter")

    def getServiceProvider(self):
        """Returns the Organization that provides the service
        """
        encounter = self.getEncounter()
        if not encounter:
            return None
        return encounter.getServiceProvider()

    def getRequester(self):
        """Returns the Requester resource (Practitioner)
        """
        return self.get("requester")

    def getLabTestID(self):
        """Returns the Lab Test ID
        """
        identifiers = self.get_identifiers()
        return identifiers.get(LAB_TEST)
