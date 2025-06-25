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

from bes.lims import messageFactory as _
from bes.lims.tamanu import api as tapi
from bes.lims.tamanu.config import SENAITE_PROFILES_CODING_SYSTEM
from bes.lims.tamanu.config import SENAITE_TESTS_CODING_SYSTEM
from bes.lims.i18n import translate as t
from bika.lims import api
from bika.lims.interfaces import IAnalysisRequest
from plone.app.layout.viewlets import ViewletBase


class TamanuObjectViewlet(ViewletBase):

    def is_visible(self):
        metadata = self.get_tamanu_metadata()
        if not metadata:
            return False
        return True

    def get_tamanu_metadata(self):
        """Returns the metadata that represents the original resource the
        current context was built from on import, if any
        """
        if tapi.is_tamanu_content(self.context):
            return tapi.get_tamanu_storage(self.context)
        return None

    def get_tamanu_metadata_url(self):
        """Returns the url that displays the original resource the current
        context was built from on import, if any
        """
        return "{}/tamanu_metadata".format(api.get_url(self.context))

    def get_codings(self, items, system):
        """Return the codes from a list of a dicts for the system specified
        """
        # TODO present at sync_tamanu as well, port to API?
        if not items:
            return []
        if not isinstance(items, list):
            items = [items]
        codings = []
        for item in items:
            coding = item.get("coding") or []
            for code in coding:
                if code.get("system") != system:
                    continue
                codings.append(code)
        return codings

    def get_missing_tests(self, meta):
        """Returns a list with the missing tests
        """
        # get the analyses present in the sample and compare
        terms = {}
        for analysis in self.context.getAnalyses(full_objects=True):
            terms[analysis.getKeyword()] = True
            terms[api.get_title(analysis)] = True

        # check analyses
        missing = []
        data = meta.get("data") or {}
        details = data.get("orderDetail")
        for coding in self.get_codings(details, SENAITE_TESTS_CODING_SYSTEM):
            # search by keyword
            code = coding.get("code")
            if terms.get(code):
                continue
            # search by title
            # TODO Fallback searches by analysis to CommercialName?
            display = coding.get("display")
            if terms.get(display):
                continue

            text = "{} ({})".format(display, code)
            missing.append(text)

        return missing

    def get_missing_profiles(self, meta):
        """Returns a list with the missing profiles
        """
        terms = {}
        for profile in self.context.getProfiles():
            key = profile.getProfileKey()
            if key:
                terms[key] = True
            terms[api.get_title(profile)] = True

        missing = []
        data = meta.get("data") or {}
        profile = data.get("code")
        for item in self.get_codings(profile, SENAITE_PROFILES_CODING_SYSTEM):
            # search by profile key
            code = item.get("code")
            if terms.get(code):
                continue
            # search by title
            display = item.get("display")
            if terms.get(display):
                continue

            text = "{} ({})".format(display, code)
            missing.append(text)

        return missing

    def get_differences(self):
        if not IAnalysisRequest.providedBy(self.context):
            return None

        meta = self.get_tamanu_metadata()
        if not meta:
            return None

        diffs = []

        # missing profiles
        missing_profiles = self.get_missing_profiles(meta)
        if missing_profiles:
            key = t(_("Missing profiles"))
            diffs.append((key, ", ".join(missing_profiles)))

        # missing tests
        missing_tests = self.get_missing_tests(meta)
        if missing_tests:
            key = t(_("Missing test"))
            diffs.append((key, ", ".join(missing_tests)))

        return diffs
