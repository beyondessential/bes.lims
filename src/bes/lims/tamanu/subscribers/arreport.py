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

from bes.lims.tamanu.tasks import diagnosticreport


def on_object_created(instance, event):
    """Event handler when a results report is created. Sends a POST back to
    the Tamanu instance for samples included in the report that have a Tamanu
    resource counterpart
    """
    samples = instance.getContainedAnalysisRequests()
    for sample in samples:
        # notify Tamanu with the DiagnosticReport if necessary
        diagnosticreport.notify(sample)
