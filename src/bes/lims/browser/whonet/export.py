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

from bes.lims.config import CULTURE_INTERPRETATION_KEYWORD
from bes.lims.utils import get_field_value
from bika.lims import api
from bika.lims.interfaces import IVerified
from datetime import datetime
from plone.app.layout.globals.interfaces import IViewView
from plone.memoize.view import memoize
from Products.CMFPlone.utils import safe_unicode
from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from senaite.ast.config import ZONE_SIZE_KEY
from senaite.ast.utils import get_antibiotics
from senaite.core.api import dtime
from senaite.core.catalog import ANALYSIS_CATALOG
from senaite.core.catalog import SETUP_CATALOG
from senaite.core.decorators import readonly_transaction
from senaite.core.interfaces import IHideActionsMenu
from senaite.patient import api as patient_api
from six import StringIO
from zope.interface import implementer


@implementer(IHideActionsMenu, IViewView)
class WHONETExportView(BrowserView):
    """View for the export of AST results to a delimited text file format that
    can be imported into WHONET software (https://www.whonet.org) through
    the data import module BacLink
    """
    template = ViewPageTemplateFile("templates/export.pt")

    @readonly_transaction
    def __call__(self):

        # Form submit toggle
        form_submitted = self.form.get("submitted", False)

        # Buttons
        form_export = self.form.get("button_export", False)

        if form_submitted and form_export:
            # Search the analyses
            analyses = self.search_analyses()
            if analyses:

                # Generate the CSV-like data for Baclink
                output = self.get_export_output(analyses)

                # Establish the HTTP response header as text/csv file
                date = datetime.now().strftime("%Y%m%d%H%M")
                set_header = self.request.RESPONSE.setHeader
                set_header("Content-Type", "text/csv")
                set_header("Content-Length", len(output))
                set_header("Cache-Control", "no-store")
                set_header("Pragma", "no-cache")
                set_header("Content-Disposition",
                           "attachment;filename=\"export%s.csv\"" % date)
                output = safe_unicode(output).encode("utf-8")
                self.request.RESPONSE.write(output)
                return

        return self.template()

    @property
    def form(self):
        """Returns the form object associated to the current request
        """
        return self.request.form or {}

    @property
    def created_from(self):
        """Returns the creation date of the oldest AST analysis to export
        """
        # Default to first day of current month
        default = datetime.now()
        default = datetime(default.year, default.month, 1)
        date_from = self.form.get("created_from", None)
        date_from = api.to_date(date_from, default=default)
        return date_from.strftime("%Y-%m-%d")

    @property
    def created_to(self):
        """Returns the creation date of the earlier AST analysis to export
        """
        date_to = self.form.get("created_to", None)
        date_to = api.to_date(date_to, default=datetime.now())
        return date_to.strftime("%Y-%m-%d")

    @memoize
    def get_ast_keywords(self):
        """Returns the keywords of analyses that indicate the sample is being
        tested for antibiotic sensitivity
        See:
        https://github.com/beyondessential/pnghealth.lims/issues/127
        https://github.com/beyondessential/pnghealth.lims/issues/133
        """
        def is_ast_keyword(keyword):
            if keyword == ZONE_SIZE_KEY:
                return True
            return self.is_culture_interpretation(keyword)

        query = {"portal_type": "AnalysisService"}
        brains = api.search(query, SETUP_CATALOG)
        keywords = map(lambda brain: brain.getKeyword, brains)
        return filter(is_ast_keyword, keywords)

    def is_culture_interpretation(self, keyword):
        """Returns whether the analysis with the keyword passed-in is
        considered a culture interpretation-like test
        https://github.com/beyondessential/pnghealth.lims/issues/127
        """
        return keyword.startswith(CULTURE_INTERPRETATION_KEYWORD)

    def search_analyses(self):
        """Returns a list of sensitivity category analyses that match with the
        creation date criteria
        """
        keywords = self.get_ast_keywords()
        query = {
            "portal_type": "Analysis",
            "review_state": ["verified", "published"],
            "getKeyword": keywords,
            "date_sampled": {
                "query": [self.created_from, self.created_to],
                "range": "min:max"},
            "sort_on": "getRequestID",
            "sort_order": "ascending"
        }

        def ast_sort(a, b):
            if a.getRequestID != b.getRequestID:
                return 0
            a_key = a.getKeyword
            b_key = b.getKeyword
            if a_key == b_key:
                return 0
            if self.is_culture_interpretation(a_key):
                return 1
            return -1

        # Skip culture interpretation analyses with a zone size counterpart
        purged = []
        current_sample_id = None
        brains = api.search(query, ANALYSIS_CATALOG)
        for brain in sorted(brains, cmp=ast_sort):
            sample_id = brain.getRequestID
            if sample_id == current_sample_id:
                if self.is_culture_interpretation(brain.getKeyword):
                    continue
            purged.append(brain)
            current_sample_id = brain.getRequestID

        # Fill with analysis objects
        analyses = map(self.get_object, purged)
        analyses = filter(None, analyses)

        # Exclude analyses that belong to not-yet-verified samples
        analyses = filter(self.is_sample_published, analyses)

        return list(analyses)

    def get_object(self, brain_object_uid, default=None):
        """Returns the object or default if not reachable
        """
        try:
            return api.get_object(brain_object_uid, default=default)
        except AttributeError:
            return default

    def is_sample_verified(self, analysis):
        """Returns whether the sample of the analysis has been verified
        """
        sample = analysis.getRequest()
        return IVerified.providedBy(sample)

    def is_sample_published(self, analysis):
        """Returns whether the sample of the analysis has been published
        """
        sample = analysis.getRequest()
        return api.get_review_status(sample) == "published"

    def get_export_output(self, analyses, delimiter=","):
        """Returns a CSV-like string with the data to be exported
        """
        # Get ZONE_SIZE analyses
        skip = filter(self.is_culture_interpretation, self.get_ast_keywords())
        zone_ans = filter(lambda an: an.getKeyword() not in skip, analyses)

        # Get all antibiotics and sort them by title
        antibiotics = get_antibiotics(zone_ans)
        antibiotics_titles = map(api.get_title, antibiotics)

        # Write the file header
        output = StringIO()
        header = [
            "Hospital",
            "Medical record number",
            "Patient first name",
            "Patient last name",
            "Birthdate",
            "Age",
            "Sex",
            "Ward",
            "Accession number",
            "Sample type",
            "Collection date",
            "Date of admission",
            "Relevant clinical information",
            "Current antibiotics",
            "Microorganism",
        ]

        header.extend(antibiotics_titles)

        def wrap_quotes(value):
            if not value:
                value = ""
            val = str(value).replace('"', '\'')
            return '"{}"'.format(val)

        # Wrap values in double-quotes
        header = map(wrap_quotes, header)
        output.write(delimiter.join(header)+"\r\n")

        # Iterate over analyses and build the data lines
        for analysis in analyses:

            # Initialize the data line
            data_line = []

            # Extend the data line with the sample info
            sample = analysis.getRequest()
            sample_info = self.get_sample_info(sample)
            data_line.extend([
                sample_info["client"],
                sample_info["mrn"],
                sample_info["patient_firstname"],
                sample_info["patient_lastname"],
                sample_info["dob"],
                sample_info["age"],
                sample_info["sex"],
                sample_info["ward"],
                sample_info["id"],
                sample_info["sample_type"],
                sample_info["date_sampled"],
                sample_info["date_received"],
                sample_info["clinical_info"],
                sample_info["antibiotics"],
            ])

            # Default values for when analysis is not a zone-size
            microorganism = "no growth"
            results = [""]*len(antibiotics)
            if analysis.getKeyword() not in skip:
                # Append the microorganism name (is the ShortTitle)
                microorganism = analysis.getShortTitle()

                # Extend with the diameter (mmg) result per antibiotic
                results = []
                for antibiotic in antibiotics:
                    # Get the result for this analysis and antibiotic
                    result = self.get_result_for(analysis, antibiotic)
                    results.append(result)

            data_line.append(microorganism)
            map(data_line.append, results)

            # Wrap values in double-quotes
            data_line = map(wrap_quotes, data_line)
            output.write(delimiter.join(data_line)+"\r\n")

        output.seek(0)

        # Get the raw data and close the stream
        data = output.getvalue()
        output.close()

        return data

    def get_result_for(self, analysis, antibiotic):
        """Extracts the result for the analysis and antibiotic passed in, if
        any. Returns None otherwise
        """
        antibiotic_uid = api.get_uid(antibiotic)
        for result in analysis.getInterimFields():
            if result.get("uid") == antibiotic_uid:
                return result.get("value", "")

        return ""

    def get_age_ymd(self, dob, date_sampled):
        return patient_api.get_age_ymd(dob, date_sampled) or ""

    def get_sample_info(self, sample):
        """Returns a dictionary that represents the sample object passed-in
        """
        mrn = sample.getMedicalRecordNumberValue()
        dob = sample.getDateOfBirth()[0]
        ward = sample.getWard()
        if ward:
            ward = api.get_title(ward)

        client = sample.getClient()
        sample_type = sample.getRawSampleType()
        date_sampled = sample.getDateSampled()
        date_received = sample.getDateReceived()
        clinical_info = sample.getClinicalInformation()
        # XXX Port CurrentAntibiotics functionality from kiribati/palau/...
        antibiotics = get_field_value(sample, "CurrentAntibiotics")
        antibiotics = antibiotics or []
        antibiotics = ", ".join(map(api.get_title, antibiotics))

        patient_field = sample.getField("PatientFullName")
        firstname = patient_field.get_firstname(sample)
        lastname = patient_field.get_lastname(sample)

        return {
            "client": api.get_title(client),
            "mrn": mrn,
            "patient_firstname": firstname,
            "patient_lastname": lastname,
            "dob": self.format_date(dob),
            "age": self.get_age_ymd(dob, date_sampled),
            "sex": sample.getSex(),
            "ward": ward,
            "id": api.get_id(sample),
            "sample_type": self.get_title(sample_type),
            "date_sampled": self.format_date(date_sampled),
            "date_received": self.format_date(date_received),
            "clinical_info": clinical_info,
            "antibiotics": antibiotics,
        }

    @memoize
    def get_title(self, uid, default=""):
        """Returns the title of the object with the uid passed in
        """
        obj = api.get_object_by_uid(uid, default=None)
        if not obj:
            return default
        return api.get_title(obj)

    def format_date(self, date_obj, default=""):
        if not dtime.is_date(date_obj):
            return default
        return dtime.to_localized_time(date_obj, long_format=False,
                                       context=self.context, default=default)
