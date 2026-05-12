# -*- coding: utf-8 -*-

import time

from BTrees.OOBTree import OOBTree
from bes.lims.tamanu import logger
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


@synchronized(max_connections=1)
def get():
    """Pops the next task whose scheduled time has elapsed
    """
    # get the tasks
    tasks = _get_tasks()

    # current time in seconds since the epoch
    now = int(time.time())

    task_id = None
    for tid, when in tasks.items():
        if when <= now:
            task_id = tid
            break

    if not task_id:
        return None

    del tasks[task_id]

    # get the name of the task and the context uid
    idx = task_id.index("-")
    uid = task_id[:idx]
    name = task_id[idx+1:]

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
    return queryAdapter(obj, ITamanuTask, name=name)


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

    # do not add unless new
    if task_id in tasks:
        return False

    # current time in seconds since the epoch + delay
    when = int(time.time()) + delay

    # add the task
    logger.info("Task %s [scheduled on %s]" % (task_id, when))
    tasks[task_id] = when
    return True
