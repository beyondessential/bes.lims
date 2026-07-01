# -*- coding: utf-8 -*-

import transaction
from datetime import datetime

from Products.Five.browser import BrowserView
from bes.lims.tamanu.tasks import queue
from bika.lims import api


class TamanuQuarantineView(BrowserView):
    """Lists quarantined Tamanu tasks and allows retry or deletion.
    Available to users with the LabManager permission.
    """

    def __call__(self):
        if self.request.method == "POST":
            form = self.request.form
            action = form.get("action")
            task_id = form.get("task_id")
            if task_id:
                if action == "retry":
                    queue.retry(task_id, delay=0)
                    transaction.commit()
                elif action == "delete":
                    queue.delete(task_id)
                    transaction.commit()
            return self.request.response.redirect(self.request.URL)
        return self.index()

    def get_quarantined_tasks(self):
        """Returns display-ready dicts for all quarantined tasks.
        """
        records = []
        for rec in queue.get_quarantined():
            obj = rec["obj"]
            if obj:
                title = "%s (%s)" % (api.get_id(obj), api.get_title(obj))
                url = api.get_url(obj)
            else:
                title = rec["uid"]
                url = ""

            records.append({
                "task_id": rec["task_id"],
                "uid": rec["uid"],
                "name": rec["name"],
                "title": title,
                "url": url,
                "quarantined_at": self._format_ts(rec["quarantined_at"]),
                "error": rec["error"],
            })
        return records

    def _format_ts(self, timestamp):
        if not timestamp:
            return ""
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
