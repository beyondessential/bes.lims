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

from bes.lims.tamanu import api as tapi

from bes.lims.tamanu.resources import TamanuResource

from bes.lims.tamanu.config import ANALYSIS_STATUSES
from bes.lims.tamanu.config import SENAITE_TESTS_CODING_SYSTEM

class Observation(TamanuResource):
    """Object that represents an Observation resource from Tamanu
    Note that this is outgoing (as opposed to incoming)
    Pass in an analysis and it will do the work to transform that into
    a FHIR object
    """
    def __init__(self, analysis):
        self.analysis = analysis

    def get_initial_test(self):
        keyword = self.analysis.getKeyword()
        return self.match_order_detail(keyword)

    def match_order_detail(self, keyword):
        keyword = self.analysis.getKeyword()
        sample = self.analysis.getRequest()
        meta = tapi.get_tamanu_storage(sample)
        data = meta.get("data") or {}
        for order_detail in data.get("orderDetail", []):
            test = tapi.get_codings(order_detail, SENAITE_TESTS_CODING_SYSTEM)
            if test:
                key = test[0].get("code")
                if key == keyword:
                    return order_detail
        return None

    def get_performer(self):
        # Adding the verificator to the performer of the Observation
        verificators = self.analysis.getVerificators()

        # The last one is the final verifier
        verifier_id = verificators[-1] if verificators else None

        # Get the full user object if needed
        if verifier_id:
            user = api.get_user(verifier_id)
            return user
        return None

    def to_fhir(self):
        """Returns the FHIR format
        """

        # generate unique ID for the observation
        obs_id = str(tapi.get_uuid(self.analysis))

        ordered_test = self.get_initial_test()

        if not ordered_test:
            name = api.get_title(self.analysis)
            fallback_code = self.match_order_detail(name) or { "coding" : [] }
            # An unmatched
            return {
                "resourceType": "Observation",
                "id": obs_id,
                "status": dict(ANALYSIS_STATUSES).get("rejected", "cancelled"),
                "code": fallback_code,
            }


        # E.g. https://hl7.org/fhir/R4B/observation-example-f001-glucose.json.html
        status = api.get_review_status(self.analysis)
        status = dict(ANALYSIS_STATUSES).get(status, "partial")
        observation = {
            "resourceType": "Observation",
            "id": obs_id,
            "status": status,
            "code": ordered_test,
        }
        # quantitative / qualitative
        if self.analysis.getStringResult() or self.analysis.getResultOptions():
            # qualitative
            observation["valueString"] = self.analysis.getFormattedResult()
        else:
            # quantitative
            observation["valueQuantity"] = {
                "value": self.analysis.getResult(),
                "unit": self.analysis.getUnit(),
            }
        performer = self.get_performer()
        if performer:
            verifier_name = api.get_user_fullname(performer)
            observation["performer"] = [
                {
                    "display": verifier_name,
                    "identifier": {
                        "value": performer.getId()
                    }
                }
            ]
        return observation

