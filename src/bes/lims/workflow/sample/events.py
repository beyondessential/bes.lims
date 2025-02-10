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

from bes.lims import utils


def after_verify(sample):
    """Event fired when a sample gets verified
    """
    # The text Insufficient volume of sample set for field "Not enough volume
    # text" (from either the Sample Type or Sample Template) is automatically
    # inserted in the "Results Interpretation" field (section "General") when
    # there is not enough volume
    # https://github.com/beyondessential/pnghealth.lims/issues/24
    if not utils.is_enough_volume(sample):
        # Rely first on the template
        template = sample.getTemplate()
        msg = template.getInsufficentVolumeText() if template else ""

        if not msg:
            # Fallback to message from sample type
            sample_type = sample.getSampleType()
            msg = sample_type.getInsufficientVolumeText() or ""

        if msg:
            # Store the message in Results Interpretation (General)
            prev = sample.getResultsInterpretation()
            msg = "<br/>".join([msg, prev])
            sample.setResultsInterpretation(msg)
