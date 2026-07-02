# -*- coding: utf-8 -*-

import time

from BTrees.OOBTree import OOBTree
from bes.lims.tamanu import logger
from bes.lims.tamanu.config import TAMANU_QUARANTINE_QUEUE
from bes.lims.tamanu.config import TAMANU_TASKS_QUEUE
from bes.lims.tamanu.interfaces import ITamanuTask
from bika.lims import api
from bika.lims.decorators import synchronized
from zope.annotation.interfaces import IAnnotations
from zope.component import queryAdapter


def _get_tasks():
    """Returns an OOBTree of pending Tamanu tasks, keyed by task_id
    (``"<uid>-<name>"``) with the scheduled-on epoch timestamp as value.

    OOBTree is used (rather than a flat ``persistent.list.PersistentList``)
    so concurrent producers inserting distinct keys do not generate
    unresolvable ConflictErrors on the underlying persistent container.
    """
    portal = api.get_portal()
    annotation = IAnnotations(portal)
    if annotation.get(TAMANU_TASKS_QUEUE) is None:
        annotation[TAMANU_TASKS_QUEUE] = OOBTree()
    return annotation[TAMANU_TASKS_QUEUE]


def _get_quarantine():
    """Returns an OOBTree of quarantined Tamanu tasks, keyed by task_id
    with a dict value containing quarantined_at timestamp and error message.
    """
    portal = api.get_portal()
    annotation = IAnnotations(portal)
    if annotation.get(TAMANU_QUARANTINE_QUEUE) is None:
        annotation[TAMANU_QUARANTINE_QUEUE] = OOBTree()
    return annotation[TAMANU_QUARANTINE_QUEUE]


def _parse_task_id(task_id):
    """Returns (uid, name) tuple parsed from a task_id string
    """
    idx = task_id.index("-")
    return task_id[:idx], task_id[idx+1:]


@synchronized(max_connections=1)
def get():
    """Pops the next non-quarantined task whose scheduled time has elapsed
    """
    # get the tasks
    tasks = _get_tasks()
    quarantine = _get_quarantine()

    # current time in seconds since the epoch
    now = int(time.time())

    task_id = None
    for tid, when in tasks.items():
        if tid in quarantine:
            # skip quarantined tasks
            continue
        if when <= now:
            task_id = tid
            break

    if not task_id:
        return None

    # remove the task from the queue
    del tasks[task_id]

    uid, name = _parse_task_id(task_id)

    # validate the task id
    if not all([name, api.is_uid(uid)]):
        logger.error("Not a valid task: %s" % task_id)
        return None

    # get the context
    obj = api.get_object_by_uid(uid, None)
    if not obj:
        logger.error("No object found for UID %s" % uid)
        return None

    # find an adapter for the given name
    adapter = queryAdapter(obj, ITamanuTask, name=name)
    if adapter is not None:
        # expose the task_id on the adapter so callers can quarantine it
        adapter.task_id = task_id
    return adapter


@synchronized(max_connections=1)
def put(name, context, delay=120):
    """Adds a task for the given name and context to the queue
    :param name: The name of the task
    :param context: Context the task is bound to
    :param delay: Minimum delay in seconds before the task is executed
    :returns: True if the task was added
    :rtype: bool
    """
    uid = api.get_uid(context)
    task_id = "%s-%s" % (uid, name)
    tasks = _get_tasks()
    quarantine = _get_quarantine()

    # do not add unless new and not in quarantine
    if task_id in tasks  or task_id in quarantine:
        return False

    # current time in seconds since the epoch + delay
    when = int(time.time()) + delay

    # add the task
    logger.info("Task %s [scheduled on %s]" % (task_id, when))
    tasks[task_id] = when
    return True


@synchronized(max_connections=1)
def quarantine(task_id, error):
    """Creates a task in the quarantine store with the given error message.
    The task will be skipped by get() until retried or deleted.
    :param task_id: The task identifier (``"<uid>-<name>"``)
    :param error: Error message or response text from the failed POST
    """
    store = _get_quarantine()
    store[task_id] = {
        "quarantined_at": int(time.time()),
        "error": str(error), # this could be later refined in bes.lims#i163
    }
    logger.warning("Task %s [quarantined]: %s" % (task_id, error))


def get_quarantined():
    """Returns a list of dicts describing all quarantined tasks.
    Each dict has: task_id, uid, name, obj, quarantined_at, error.
    """
    store = _get_quarantine()
    records = []
    for task_id, info in store.items():
        uid, name = _parse_task_id(task_id)
        obj = api.get_object_by_uid(uid, None)
        records.append({
            "task_id": task_id,
            "uid": uid,
            "name": name,
            "obj": obj,
            "quarantined_at": info.get("quarantined_at", 0),
            "error": info.get("error", ""),
        })
    return records


@synchronized(max_connections=1)
def retry(task_id, delay=0):
    """Removes a task from quarantine and reschedules it in the active queue.
    :param task_id: The task identifier
    :param delay: Seconds to wait before the task becomes eligible (default 0)
    :returns: True if the task was found in quarantine and rescheduled
    :rtype: bool
    """
    store = _get_quarantine()
    if task_id not in store:
        logger.warning("Task %s not in quarantine, cannot retry" % task_id)
        return False

    del store[task_id]

    tasks = _get_tasks()
    when = int(time.time()) + delay
    tasks[task_id] = when
    logger.info("Task %s [retried, scheduled on %s]" % (task_id, when))
    return True


@synchronized(max_connections=1)
def delete(task_id):
    """Permanently removes a task from the quarantine store and task store
    :param task_id: The task identifier
    :returns: True if the task was found and removed
    :rtype: bool
    """
    store = _get_quarantine()
    if task_id not in store:
        logger.warning("Task %s not in quarantine, cannot delete" % task_id)
        return False

    del store[task_id]
    logger.info("Task %s [deleted from quarantine]" % task_id)

    # Now remove from tasks - note an error here is not critical as it will
    # amount to a retry given the task_id is removed from quarantine (no longer
    # a skipped task)
    tasks = _get_tasks()
    if task_id not in tasks:
        logger.warning("Task %s not in found in tasks, cannot delete" % task_id)
        return False

    del tasks[task_id]
    logger.info("Task %s [deleted from tasks]" % task_id)
    return True
