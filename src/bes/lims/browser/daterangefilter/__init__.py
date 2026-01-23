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

from datetime import datetime
from datetime import timedelta
import json
from zope.globalrequest import getRequest

# Cookie storage key
DATERANGE_FILTER_COOKIE = "daterange_filter_cookie"


def get_selected_date_range_config():
    """Returns the date range (from, to, type) currently selected.

    If no date range was explicitly selected in the UI, the
    function defaults to returning the current month range.
    """
    request = getRequest()
    now = datetime.now()

    # Default date range congiguration
    delta = now - timedelta(days=30)
    date_from = delta.strftime("%Y-%m-%d 00:00")
    date_to = now.strftime("%Y-%m-%d 23:59")
    date_type = "created"
    filter_enabled = False

    cookie_raw = request.cookies.get(DATERANGE_FILTER_COOKIE, None)

    if cookie_raw:
        cookie_data = json.loads(cookie_raw)
        date_from = cookie_data.get("datetime_from", date_from)
        date_to = cookie_data.get("datetime_to", date_to)
        date_type = cookie_data.get("date_type", date_type)
        filter_enabled = cookie_data.get("filter_enabled", filter_enabled)

    return {
        "datetime_from": date_from,
        "datetime_to": date_to,
        "date_type": date_type,
        "filter_enabled": filter_enabled
    }


def set_selected_date_range_config(
    datetime_from, datetime_to, date_type, filter_enabled=False
):
    """
    Sets the datetime range, type, and filter enabled state in cookie storage
    """
    request = getRequest()
    if not request:
        return

    cookie_value = json.dumps({
        "datetime_from": datetime_from,
        "datetime_to": datetime_to,
        "date_type": date_type,
        "filter_enabled": bool(filter_enabled),
    })

    # Persist cookie for the next request
    request.response.setCookie(
        DATERANGE_FILTER_COOKIE,
        cookie_value,
        quoted=False,
        path="/"
    )

    # Update current request state so the new value is visible immediately
    if hasattr(request, "cookies"):
        request.cookies[DATERANGE_FILTER_COOKIE] = cookie_value
