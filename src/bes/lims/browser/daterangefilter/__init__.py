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

from zope.globalrequest import getRequest

# Session storage key
SESSION_KEY = "daterangefilter.storage"


def get_selected_date_range():
    """Returns the date range (from, to, type) currently selected.

    If no date range was explicitly selected in the UI, the
    function defaults to returning the current month range.
    """
    request = getRequest()
    if request and hasattr(request, 'SESSION'):
        session_data = request.SESSION.get(SESSION_KEY)
        if session_data:
            return session_data

    # Default to current month and created date type
    datetime_from = ""
    datetime_to = ""

    return {
        "datetime_from": datetime_from,
        "datetime_to": datetime_to,
        "date_type": "created"
    }


def set_selected_date_range(datetime_from, datetime_to, date_type):
    """Sets the datetime range and type in session storage"""
    request = getRequest()
    if request and hasattr(request, 'SESSION'):
        request.SESSION[SESSION_KEY] = {
            "datetime_from": datetime_from,
            "datetime_to": datetime_to,
            "date_type": date_type
        }
