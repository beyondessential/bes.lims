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

from bika.lims import api
from Products.Five import BrowserView
from senaite.core.api import dtime
from six import StringIO


class CSVReport(BrowserView):

    @property
    def report_id(self):
        return self.request.form["report_id"]

    def __call__(self):
        # get the rows
        rows = self.process_form()

        # convert to csv
        csv_data = self.to_csv(rows)

        # download the csv
        return self.download(csv_data)

    def process_form(self):
        """Returns a list of rows with same number of columns
        """
        raise NotImplementedError("Not implemented")

    def to_csv(self, rows):
        """Returns a CSV-like string with quotes values
        """
        output = StringIO()
        for row in rows:
            output.write(",".join(map(self.quote, row)) + "\n")
        return output.getvalue()

    def quote(self, value):
        """Adds double quotes around the value
        """
        # strip empty spaces
        value = str(value).strip()
        # strip " and replace " by '
        value = value.strip("\"").replace("\"", "'")
        return "\"{}\"".format(value)

    def download(self, data):
        """Adds the response headers for data download
        """
        now = dtime.to_ansi(datetime.now())
        filename = "{}-{}.csv".format(self.report_id, now)
        output = api.safe_unicode(data).encode("utf-8")
        set_header = self.request.response.setHeader
        set_header("Content-Disposition", "attachment; filename={}"
                   .format(filename))
        set_header("Content-Type", "text/csv")
        set_header("Content-Length", len(output))
        set_header("Cache-Control", "no-store")
        set_header("Pragma", "no-cache")
        self.request.response.write(output)
        return output
