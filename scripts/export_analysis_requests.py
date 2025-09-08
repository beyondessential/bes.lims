# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# BES.LIMS is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, version 2.
#
# This program is distributed in the hope that itdef main(app):
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


import argparse
from collections import OrderedDict
import logging
import os
import re
from datetime import timedelta

from bes.lims import logger
from bes.lims import messageFactory as _
from bes.lims.scripts import setup_script_environment
from bes.lims.setuphandlers import deactivate
from bes.lims.utils import is_reportable
from bika.lims import api
from bika.lims.utils import format_supsub
from bika.lims.utils import to_utf8
from senaite.core.api import dtime
from senaite.core.catalog import ANALYSIS_CATALOG
from senaite.core.i18n import translate
from senaite.patient.api import get_age_ymd
from senaite.patient.config import SEXES
from six import StringIO


__doc__ = """
Export SENAITE analysis requests by date range.
This script exports analysis requests within a specified date range
to a CSV file.
"""

parser = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)

# Define the command line arguments
parser.add_argument(
    "-df", "--date_from",
    help='Start date for verified analyses (YYYY-MM-DD format). Default: '
         'first day of previous week'
)

parser.add_argument(
    "-dt", "--date_to",
    help='End date for verified analyses (YYYY-MM-DD format). Default: '
         'last day of previous week'
)

parser.add_argument(
    "-d", "--destination",
    help='Destination directory for the CSV file',
)

parser.add_argument(
    "-v", "--verbose", action="store_true",
    help="Verbose logging"
)

# Define the columns
COLUMNS = OrderedDict((
    ("sample_id", {
        "title": _("Sample ID"),
    }),
    ("tamanu_id", {
        "title": _("Tamanu ID"),
    }),
    ("sample_type", {
        "title": _("Sample Type"),
    }),
    ("age", {
        "title": _("Patient Age"),
    }),
    ("gender", {
        "title": _("Patient Gender"),
    }),
    ("collected", {
        "title": _("Date and time Collected"),
    }),
    ("created", {
        "title": _("Date and time Registered"),
    }),
    ("captured", {
        "title": _("Date and time Tested"),
    }),
    ("verified", {
        "title": _("Date and time Verified"),
    }),
    ("published", {
        "title": _("Date and time Published"),
    }),
    ("category", {
        "title": _("Test Category"),
    }),
    ("department", {
        "title": _("Test Department"),
    }),
    ("test_id", {
        "title": _("Test ID"),
    }),
    ("test_type", {
        "title": _("Test Type"),
    }),
    ("panels", {
        "title": _("Test Panels"),
    }),
    ("result", {
        "title": _("Test Result (with units)"),
    }),
    ("status", {
        "title": _("Test Status"),
    }),
    ("site", {
        "title": _("Site"),
    }),
))


def get_dates_range(date_from, date_to):
    """Parse and validate date range
    """
    if date_from and not dtime.is_date(date_from):
        raise ValueError("Invalid date format. Use YYYY-MM-DD")

    if date_to and not dtime.is_date(date_to):
        raise ValueError("Invalid date format. Use YYYY-MM-DD")

    now = dtime.now()
    if not date_from:
        # defaults to first day of the previous week
        date_from = now - timedelta(days=now.weekday() + 7)

    if not date_to:
        # defaults to last day of the previous week
        date_to = now - timedelta(days=now.weekday() + 1)

    # to earliest and latest
    date_from = dtime.to_DT(date_from).earliestTime()
    date_to = dtime.to_DT(date_to).latestTime()
    if date_from >= date_to:
        raise ValueError("To date must be after from date")

    return date_from, date_to


def get_age(dob, sampled):
    """Returns the age truncated to the highest period
    """
    ymd = get_age_ymd(dob, sampled)
    if not ymd:
        return ""
    # truncate to highest period
    matches = re.match(r"^(\d+[ymd])", ymd)
    return matches.groups()[0] if matches else ""


def parse_date_to_output(date):
    """Parse date to localized string format
    """
    return dtime.to_localized_time(date, long_format=True) or ""


def get_analysis_profiles(sample):
    """Get analysis profiles for sample
    """
    profiles = sample.getProfiles()
    return [api.get_title(profile) for profile in profiles]


def get_header_row():
    """Returns a plain list with the column names
    """
    return [COLUMNS[key].get("title") for key in COLUMNS.keys()]


def get_row_info(analysis, sample):
    """Get row information for analysis
    """
    sampled = sample.getDateSampled()
    dob = sample.getDateOfBirth()[0]
    age = get_age(dob, sampled)

    # Date formatting
    sampled = parse_date_to_output(sampled)
    created = parse_date_to_output(sample.created())
    result_captured = parse_date_to_output(
        analysis.getResultCaptureDate()
    )
    result_verified = parse_date_to_output(
        analysis.getDateVerified()
    )
    result_published = parse_date_to_output(
        analysis.getDatePublished()
    )

    # Only show results that appear on the final reports
    result = analysis.getResult() or ""

    # Get the department title
    department = analysis.getDepartment()
    department_title = api.get_title(department) if department else ""

    # Get category
    category = analysis.getCategoryUID()
    category_title = api.get_title(category) if category else ""

    # Get profiles/panels
    profiles = get_analysis_profiles(sample)

    # Format unit
    unit = format_supsub(to_utf8(analysis.Unit)) if analysis.Unit else ""

    # Get the patient's gender/sex
    gender = dict(SEXES).get(sample.getSex())
    gender = translate(gender) if gender else ""

    # Get analysis status
    status = api.get_review_status(analysis)

    return {
        "sample_id": analysis.getRequestID(),
        "tamanu_id": sample.getClientSampleID() or "",
        "sample_type": sample.getSampleTypeTitle() or "",
        "age": age,
        "gender": gender,
        "collected": sampled,
        "created": created,
        "captured": result_captured,
        "verified": result_verified,
        "published": result_published,
        "department": department_title,
        "category": category_title,
        "panels": ", ".join(profiles),
        "test_id": analysis.getId() or "",
        "test_type": analysis.Title(),
        "result": result + (" " + unit if unit else ""),
        "status": status,
        "site": sample.getClientTitle() or ""
    }


def do_export(date_from, date_to, output_file):
    """Export data to CSV file
    """
    # Get published analyses that were verified within the given date range
    query = {
        "portal_type": "Analysis",
        "review_state": ["published"],
        "date_verified": {
            "query": [date_from, date_to],
            "range": "min:max",
        },
        "sort_on": "getDateReceived",
        "sort_order": "ascending",
    }

    logger.info(
        "Exporting analyses from %s to %s ..." % (
            dtime.date_to_string(date_from),
            dtime.date_to_string(date_to)
        )
    )

    # Generate one row per analysis
    rows = []
    for brain in api.search(query, ANALYSIS_CATALOG):
        analysis = api.get_object(brain)
        if not is_reportable(analysis):
            analysis._p_deactivate()
            continue

        # build the analysis row
        sample = analysis.getRequest()
        info = get_row_info(analysis, sample)
        row = [info.get(key, "") for key in COLUMNS.keys()]
        rows.append(row)

        # flush the sample and analysis from memory
        analysis._p_deactivate()  # noqa
        sample._p_deactivate()  # noqa

    # Insert the header row at first position
    rows.insert(0, get_header_row())

    # generate the csv
    to_csv(rows, output_file)

    logger.info(
        "Exporting analyses from %s to %s [DONE]" % (
            dtime.date_to_string(date_from),
            dtime.date_to_string(date_to)
        )
    )


def quote(value):
    """Adds double quotes around the value
    """
    # strip empty spaces
    value = str(value).strip()
    # strip " and replace " by '
    value = value.strip("\"").replace("\"", "'")
    return "\"{}\"".format(value)


def to_csv(rows, output_file):
    """Returns a CSV-like string with quotes values
    """
    output = StringIO()
    for row in rows:
        output.write(",".join(map(quote, row)) + "\n")

    output = api.safe_unicode(output.getvalue()).encode("utf-8")
    with open(output_file, 'w') as f:
        f.write(output)


def main(app):
    """Main entry point for the script"""

    args, _ = parser.parse_known_args()
    if hasattr(args, "help") and args.help:
        print("")
        parser.print_help()
        parser.exit()

    # Setup environment
    setup_script_environment(app, stream_out=True)

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # destination path
    destination = args.destination or os.getcwd()
    if not os.path.exists(destination):
        print("Destination directory does not exist: {}", args.destination)
        exit(-1)

    # compute the date range (default: previous week)
    try:
        dt_from, dt_to = get_dates_range(args.date_from, args.date_to)
    except ValueError as e:
        print(str(e))
        exit(-1)

    # output file
    ansi_from = dtime.to_ansi(dt_from, show_time=False)
    ansi_to = dtime.to_ansi(dt_to, show_time=False)
    filename = "analyses-%s-%s.csv" % (ansi_from, ansi_to)
    out_file = os.path.join(destination, filename)

    # export the data
    do_export(dt_from, dt_to, out_file)


if __name__ == "__main__":
    main(app)  # noqa: F821
