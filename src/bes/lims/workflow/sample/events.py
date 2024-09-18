# -*- coding: utf-8 -*-

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
