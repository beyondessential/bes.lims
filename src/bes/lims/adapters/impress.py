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

import transaction
from bes.lims import logger
from bika.lims import api
from senaite.impress.decorators import synchronized
from senaite.impress.storage import PdfReportStorageAdapter as BaseAdapter
from bika.lims.workflow import doActionFor as do_action_for
from PyPDF2 import PdfMerger
from StringIO import StringIO


class PdfReportStorageAdapter(BaseAdapter):
    """Storage adapter for PDF reports with PDF attachment support
    """

    def get_pdf_attachments(self, parent):
        """Get PDF attachments that are flagged for rendering in report
        """
        pdf_attachments = []

        # Get sample attachments
        attachments = parent.getAttachment()

        for attachment in attachments:
            if not attachment.getRenderInReport():
                continue

            attachment_file = attachment.getAttachmentFile()
            if not attachment_file:
                continue

            # Check if it's a PDF
            content_type = attachment_file.getContentType()
            if content_type and content_type.lower() == 'application/pdf':
                pdf_attachments.append(attachment)

        return pdf_attachments

    def merge_pdf_attachments(self, main_pdf, attachments):
        """Merge PDF attachments into the main PDF
        """
        if not attachments:
            return main_pdf

        # Create PDF merger
        merger = PdfMerger()

        main_pdf_stream = StringIO(main_pdf)
        merger.append(main_pdf_stream)

        # Add each PDF attachment
        for attachment in attachments:
            attachment_file = attachment.getAttachmentFile()
            attachment_data = attachment_file.data
            attachment_stream = StringIO(attachment_data)
            merger.append(attachment_stream)

        output = StringIO()
        merger.write(output)
        merged_pdf = output.getvalue()
        output.close()
        merger.close()

        return merged_pdf

    @synchronized(max_connections=1)
    def create_report(self, parent, pdf, html, uids, metadata):
        """Create a new report object

        NOTE: We limit the creation of reports to 1 to avoid conflict errors on
              simultaneous publication.

        :param parent: parent object where to create the report inside
        :returns: ARReport
        """

        parent_id = api.get_id(parent)
        logger.info("Create Report for {} ...".format(parent_id))

        # Manually update the view on the database to avoid conflict errors
        parent._p_jar.sync()

        # Get PDF attachments that should be merged
        pdf_attachments = self.get_pdf_attachments(parent)

        # Merge PDF attachments into the main PDF if any exist
        if pdf_attachments:
            pdf = self.merge_pdf_attachments(pdf, pdf_attachments)

        # Create the report object
        report = api.create(
            parent,
            "ARReport",
            AnalysisRequest=api.get_uid(parent),
            Pdf=pdf,
            Html=html,
            ContainedAnalysisRequests=uids,
            Metadata=metadata)

        # Transition the sample to published status
        do_action_for(parent, "publish")

        # Commit the changes
        transaction.commit()

        logger.info("Create Report for {} [DONE]".format(parent_id))

        return report
