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
from bika.lims.interfaces import IGuardAdapter
from senaite.ast import utils
from senaite.ast.config import DISK_CONTENT_KEY
from senaite.ast.config import MIC_KEY
from senaite.ast.config import ZONE_SIZE_KEY
from zope.interface import implementer

from bes.lims.adapters.guards import BaseGuardAdapter

OPERATORS = ["<=", ">=", "<", ">"]


@implementer(IGuardAdapter)
class AnalysisGuardAdapter(BaseGuardAdapter):
    """Adapter for Analysis guards
    """

    def strip_operator(self, value):
        """Strip optional comparator operator from value
        """
        value = (value or "").strip()
        operator = filter(lambda p: value.startswith(p), OPERATORS)
        if operator:
            value = value.replace(operator[0], "")
        return value.strip()

    def guard_submit(self):
        """Allow comparator-prefixed values in AST numeric interim fields"""
        if not utils.is_ast_analysis(self.context):
            # Not an AST analysis
            return True

        # Get the antibiotics (as interim fields)
        antibiotics = self.context.getInterimFields()
        if not antibiotics:
            return False

        keyword = self.context.getKeyword()
        for antibiotic in antibiotics:
            if utils.is_extrapolated_interim(antibiotic):
                # Skip extrapolated antibiotics
                continue

            if utils.is_rejected_interim(antibiotic):
                # Skip rejected antibiotics
                continue

            if utils.is_interim_empty(antibiotic):
                # Cannot submit if no result
                return False

            if keyword in [ZONE_SIZE_KEY, DISK_CONTENT_KEY]:
                # operators '>', '>=', '<' and '<=' are permitted
                value = self.strip_operator(antibiotic.get("value"))

                # Negative values are not permitted.
                value = api.to_float(value, default=-1)
                if value < 0:
                    return False

            if keyword in [MIC_KEY]:
                # operators '>', '>=', '<' and '<=' are permitted
                value = self.strip_operator(antibiotic.get("value"))

                numerator, slash, denominator = value.partition("/")

                # denominator with 0 or negative values are not permitted
                if slash and api.to_float(denominator, default=-1) <= 0:
                    return False

                # numerator of zero or below 0 is not supported
                numerator = api.to_float(numerator, default=-1)
                if numerator < 0:
                    return False
                elif slash and numerator <= 0:
                    return False

        return True
