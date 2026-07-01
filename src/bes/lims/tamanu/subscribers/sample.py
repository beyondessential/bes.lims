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
from bes.lims.tamanu import logger
from bes.lims.tamanu.tasks import diagnosticreport
from bika.lims import api
from senaite.core.api import dtime
from senaite.impress.interfaces import IPdfReportStorage
from senaite.impress.publishview import PublishView
from zope.component import getMultiAdapter


def _generate_invalidation_report(success, uid=None, request=None):
    """After-commit hook that generates and stores a report for the invalidated
    sample. Runs in a fresh transaction after the invalidate has committed, so
    the sample state is already 'invalid' and _p_jar.sync() in the storage
    adapter does not roll back the transition.
    """
    if not success:
        return
    try:
        obj = api.get_object_by_uid(uid)
        if not obj:
            return
        view = PublishView(obj, request)
        reports = view.generate_reports_for([uid])
        if not reports:
            logger.warning(
                "No report generated for invalidated sample %s" % uid)
            return
        report = reports[0]
        timestamp = dtime.DateTime().ISO()
        meta = report.get_metadata(contained_requests=[uid], timestamp=timestamp)
        storage = getMultiAdapter((obj, request), IPdfReportStorage)
        storage.store(report.pdf, report.html, [uid], metadata=meta)
    except Exception:
        logger.error(
            "Failed to generate invalidation report for %s" % uid,
            exc_info=True)


def after_invalidate(obj):
    """Registers an after-commit hook to generate and store a watermarked PDF
    report for the invalidated sample.

    Report generation is deferred to after the invalidate transaction commits
    because the storage adapter calls _p_jar.sync(), which would abort the
    in-progress transaction and revert the state change.
    """
    uid = api.get_uid(obj)
    request = api.get_request()
    transaction.get().addAfterCommitHook(
        _generate_invalidation_report,
        kws={"uid": uid, "request": request})


def on_after_transition(sample, event):  # noqa camelcase
    """Actions to be done when a transition for a sample takes place
    """
    if not event.transition:
        return

    if event.transition.id == "invalidate":
        after_invalidate(sample)

    # notify Tamanu with the DiagnosticReport if necessary
    diagnosticreport.notify(sample)
