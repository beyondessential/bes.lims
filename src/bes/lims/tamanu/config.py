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

TAMANU_USER = "tamanu"

TAMANU_STORAGE = "senaite.tamanu.storage"

TAMANU_SEXES = (
    ("male", "m"),
    ("female", "f"),
    ("", ""),
)

SNOMED_CODING_SYSTEM = "http://snomed.info/sct"
LOINC_CODING_SYSTEM = "http://loinc.org"
SENAITE_TESTS_CODING_SYSTEM = "https://www.senaite.com/testCodes.html"
SENAITE_PROFILES_CODING_SYSTEM = "https://www.senaite.com/profileCodes.html"

LOINC_GENERIC_DIAGNOSTIC = (
    # Generic LOINC code 30954-2 (https://loinc.org/30954-2) that is used by
    # default in DiagnosticReport callbacks when no panel was defined in the
    # original Tamanu's ServiceRequest
    ("system", "http://loinc.org"),
    ("code", "30954-2"),
    ("display", "Relevant Dx tests/lab data"),
)

SAMPLE_FINAL_STATUSES = (
    # sample statuses in SENAITE considered as "final", that are not editable
    # through synchronization with Tamanu
    "cancelled",
    "rejected",
    "published",
    "invalid",
)
