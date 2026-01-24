# -*- coding: utf-8 -*-

import time

from bes.lims.tamanu import logger
from bes.lims.tamanu.config import TAMANU_TASKS_QUEUE
from bes.lims.tamanu.interfaces import ITamanuTask
from bika.lims import api
from bika.lims.decorators import synchronized
from persistent.list import PersistentList
from zope.annotation.interfaces import IAnnotations
from zope.component import queryAdapter


def _get_tasks():
    """Returns a PersistentList containing a list of dicts, each representing
    a Tamanu task, sorted reverse, from newest to oldest
    """
    portal = api.get_portal()
    annotation = IAnnotations(portal)
    if annotation.get(TAMANU_TASKS_QUEUE) is None:
        annotation[TAMANU_TASKS_QUEUE] = PersistentList()
    return annotation[TAMANU_TASKS_QUEUE]


@synchronized(max_connections=1)
def get():
    """Pops the next task to be processed
    """
    # get the tasks
    tasks = _get_tasks()

    # current time in seconds since the epoch
    now = int(time.time())

    # first elements added have priority (FIFO)
    task = None
    for idx in range(len(tasks)):
        # check if the task has to be delayed
        if tasks[idx][1] <= now:
            task = tasks.pop(idx)[0]
            break

    # no task found
    if not task:
        return None

    # get the name of the task and the context uid
    idx = task.index("-")
    uid = task[:idx]
    name = task[idx+1:]

    # validate the task id
    if not all([name, api.is_uid(uid)]):
        logger.error("Not a valid task: %s" % task)
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
    """Appends a task for the given name and context to the queue
    :param name: The name of the task
    :param context: Context the task is bound to
    :param delay: Minimum delay in seconds before the task is executed
    :returns: True if the task was added
    :rtype: bool
    """
    uid = api.get_uid(context)
    task_id = "%s-%s" % (uid, name)
    tasks = _get_tasks()

    # do not append unless new
    ids = [task[0] for task in tasks]
    if task_id in ids:
        return False

    # current time in seconds since the epoch + delay
    when = int(time.time()) + delay

    # add the task
    logger.info("Task %s [scheduled on %s]" % (task_id, when))
    tasks.append((task_id, when))
    return True
