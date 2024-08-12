# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# Copyright 2024 Beyond Essential Systems Pty Ltd

from bes.lims import _
from Products.Archetypes import DisplayList


ANALYSIS_REPORTABLE_STATUSES = (
    "to_be_verified",
    "verified",
    "published",
    "out_of_stock",
)

MONTHS = {
    1: _("January"),
    2: _("February"),
    3: _("March"),
    4: _("April"),
    5: _("May"),
    6: _("June"),
    7: _("July"),
    8: _("August"),
    9: _("September"),
    10: _("October"),
    11: _("November"),
    12: _("December")
}

TARGET_PATIENTS = DisplayList((
    ("a", _("Adult patient")),
    ("p", _("Paediatric patient")),
))
