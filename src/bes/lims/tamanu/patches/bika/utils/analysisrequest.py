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

from bes.lims import logger
from bes.lims.tamanu import api as tapi
from bes.lims.tamanu.config import LOINC_CODING_SYSTEM
from bes.lims.tamanu.config import LOINC_GENERIC_DIAGNOSTIC
from bika.lims import api
from bika.lims.api.mail import send_email
from bika.lims.utils.analysisrequest import get_rejection_mail
from bika.lims.utils.analysisrequest import get_rejection_pdf
from bika.lims.workflow import doActionFor
from senaite.core.api import dtime


def do_rejection(sample, notify=None):
    """Rejects the sample and if succeeds, generates the rejection pdf and
    sends a notification email. If notify is None, the notification email will
    only be sent if the setting in Setup is enabled
    """
    sample_id = api.get_id(sample)
    if not sample.getRejectionReasons():
        logger.warn("Cannot reject {} w/o rejection reasons".format(sample_id))
        return

    success, msg = doActionFor(sample, "reject")
    if not success:
        logger.warn("Cannot reject the sample {}".format(sample_id))
        return

    # Generate a pdf with the rejection reasons
    pdf = get_rejection_pdf(sample)

    # Attach the PDF to the sample
    filename = "{}-rejected.pdf".format(sample_id)
    attachment = sample.createAttachment(pdf, filename=filename)
    pdf_file = attachment.getAttachmentFile()

    # Notify Tamanu back about the rejection report
    send_rejection_report(sample, attachment)

    # Do we need to send a notification email?
    if notify is None:
        setup = api.get_setup()
        notify = setup.getNotifyOnSampleRejection()

    if notify:
        # Compose and send the email
        mime_msg = get_rejection_mail(sample, pdf_file)
        if mime_msg:
            # Send the email
            send_email(mime_msg)


def send_rejection_report(sample, report):
    """Sends a DiagnosticReport notification to Tamanu
    """
    # get the tamanu session
    session = tapi.get_tamanu_session_for(sample)
    if not session:
        return

    # get the uuid of the rejection report
    report_uuid = str(tapi.get_uuid(report))

    # get the original data
    meta = tapi.get_tamanu_storage(sample)
    data = meta.get("data") or {}

    # modification date
    modified = api.get_creation_date(sample)
    modified = dtime.to_iso_format(modified)

    # build the payload
    # TODO Add an adapter to build payloads for a given object (e.g Attachment)
    tamanu_uid = tapi.get_tamanu_uid(sample)
    payload = {
        # meta information about the DiagnosticReport
        "resourceType": "DiagnosticReport",
        "id": report_uuid,
        "meta": {
            "lastUpdated": modified,
        },
        # the status of the DiagnosticReport
        # registered | partial | preliminary | final | entered-in-error
        "status": "cancelled",
        # the ServiceRequest(s) this ARReport is based on
        # TODO What about a DiagnosticReport with more than one basedOn
        "basedOn": [{
            "type": "ServiceRequest",
            "reference": "ServiceRequest/{}".format(tamanu_uid),
        }],
    }

    # add the test panel (profile) if set or use LOINC's generic
    # tamanu doesn't recognizes more than one coding, keep only the LOINC one
    coding = [dict(LOINC_GENERIC_DIAGNOSTIC)]
    panel = data.get("code") or {}
    for code in panel.get("coding") or []:
        if code.get("system") == LOINC_CODING_SYSTEM:
            coding = [code]
            break
    payload["code"] = {"coding": coding}

    # attach the pdf encoded in base64
    pdf = report.getAttachmentFile()
    payload["presentedForm"] = [{
        "data": pdf.data.encode("base64"),
        "contentType": "application/pdf",
        "title": api.get_id(sample),
    }]

    # notify back to Tamanu
    session.post("DiagnosticReport", payload)
