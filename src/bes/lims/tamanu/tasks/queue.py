# -*- coding: utf-8 -*-

from bika.lims import api
from bika.lims.decorators import synchronized
from persistent.list import PersistentList
from zope.annotation.interfaces import IAnnotations
from zope.component import queryAdapter

from bes.lims.tamanu import logger
from bes.lims.tamanu.config import TAMANU_TASKS_QUEUE
from bes.lims.tamanu.interfaces import ITamanuTask


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
    tasks = _get_tasks()
    if not tasks:
        return None

    # pop the oldest element (last from the list)
    task = tasks.pop()
    if not task:
        return None

    # get the name of the task and the context uid
    idx = task.indexOf("-")
    uid = task[:idx]
    name = task[idx:]

    # validate the task id
    if not all([name,api.is_uid(uid)]):
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
def put(name, context):
    """Appends a task for the given name and context to the queue
    """
    uid = api.get_uid(context)
    task_id = "%s-%s" % (uid, name)
    tasks = _get_tasks()
    # do not append unless new
    if name not in tasks:
        tasks.insert(0, task_id)
