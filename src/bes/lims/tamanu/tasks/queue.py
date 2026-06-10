# -*- coding: utf-8 -*-

import time

from BTrees.OOBTree import OOBTree
from bes.lims.tamanu import logger
from bes.lims.tamanu.config import TAMANU_TASKS_DEADLETTER
from bes.lims.tamanu.config import TAMANU_TASKS_QUEUE
from bes.lims.tamanu.interfaces import ITamanuTask
from bika.lims import api
from bika.lims.decorators import synchronized
from zope.annotation.interfaces import IAnnotations
from zope.component import queryAdapter

# Maximum number of times a task is retried before it is moved to the
# dead-letter store. Transient failures (Tamanu briefly unreachable) recover
# within these retries; a persistently failing task (e.g. a bad record Tamanu
# keeps rejecting) is parked instead of blocking the queue head forever.
MAX_ATTEMPTS = 5

# Base back-off in seconds between retries. The delay grows with the attempt
# count (attempt * RETRY_BACKOFF) so a failing task moves out of the head and
# does not get hammered every cron cycle.
RETRY_BACKOFF = 300


def _get_tasks():
    """Returns an OOBTree of pending Tamanu tasks, keyed by task_id
    (``"<uid>-<name>"``).

    The value is the scheduled-on epoch timestamp. For backward compatibility
    the value may be a bare int (legacy entries) or a dict with ``when`` and
    ``attempts`` keys (entries that have been retried at least once); use
    :func:`_when` / :func:`_attempts` to read it regardless of shape.

    OOBTree is used (rather than a flat ``persistent.list.PersistentList``)
    so concurrent producers inserting distinct keys do not generate
    unresolvable ConflictErrors on the underlying persistent container.
    """
    portal = api.get_portal()
    annotation = IAnnotations(portal)
    if annotation.get(TAMANU_TASKS_QUEUE) is None:
        annotation[TAMANU_TASKS_QUEUE] = OOBTree()
    return annotation[TAMANU_TASKS_QUEUE]


def _get_deadletter():
    """Returns an OOBTree of tasks that exhausted their retries, keyed by
    task_id with a dict value (error, attempts, failed_on epoch).
    """
    portal = api.get_portal()
    annotation = IAnnotations(portal)
    if annotation.get(TAMANU_TASKS_DEADLETTER) is None:
        annotation[TAMANU_TASKS_DEADLETTER] = OOBTree()
    return annotation[TAMANU_TASKS_DEADLETTER]


def _when(value):
    """Returns the scheduled-on epoch from a queue value (int or dict)
    """
    if isinstance(value, dict):
        return value.get("when", 0)
    return value


def _attempts(value):
    """Returns the attempt count from a queue value (int or dict)
    """
    if isinstance(value, dict):
        return value.get("attempts", 0)
    return 0


@synchronized(max_connections=1)
def get():
    """Pops the next task whose scheduled time has elapsed.

    :returns: a ``(task_id, task)`` tuple. ``(None, None)`` when no task is
        ready. ``(task_id, None)`` when the head task was popped but cannot be
        resolved (invalid id or its context no longer exists) and should be
        dropped by the caller.
    """
    # get the tasks
    tasks = _get_tasks()

    # current time in seconds since the epoch
    now = int(time.time())

    task_id = None
    for tid, value in tasks.items():
        if _when(value) <= now:
            task_id = tid
            break

    if not task_id:
        return None, None

    del tasks[task_id]

    # get the name of the task and the context uid
    idx = task_id.index("-")
    uid = task_id[:idx]
    name = task_id[idx+1:]

    # validate the task id
    if not all([name, api.is_uid(uid)]):
        logger.error("Not a valid task: %s" % task_id)
        return task_id, None

    # get the context
    obj = api.get_object_by_uid(uid, None)
    if not obj:
        logger.error("No object found for UID %s" % uid)
        return task_id, None

    # find an adapter for the given name
    return task_id, queryAdapter(obj, ITamanuTask, name=name)


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
    tasks[task_id] = {"when": when, "attempts": 0}
    return True


@synchronized(max_connections=1)
def fail(task_id, error=""):
    """Records a failed processing attempt for the given task.

    Increments the attempt counter and either re-schedules the task with a
    back-off (so it leaves the queue head and is retried later) or, once
    ``MAX_ATTEMPTS`` is reached, moves it to the dead-letter store so it stops
    blocking the queue while remaining visible for inspection/re-injection.

    Must be called in a fresh transaction (i.e. after aborting the failed
    processing transaction), so the requeue/dead-letter is durable regardless
    of what the failed task did.

    :returns: True if the task was re-scheduled, False if it was dead-lettered
    """
    tasks = _get_tasks()
    value = tasks.get(task_id)
    if value is None:
        # the task is no longer in the queue (already handled elsewhere)
        return False

    attempts = _attempts(value) + 1
    now = int(time.time())

    if attempts < MAX_ATTEMPTS:
        when = now + attempts * RETRY_BACKOFF
        tasks[task_id] = {"when": when, "attempts": attempts}
        logger.warning(
            "Task %s failed (attempt %s/%s), retry on %s: %s"
            % (task_id, attempts, MAX_ATTEMPTS, when, error))
        return True

    # exhausted retries: park in the dead-letter store
    del tasks[task_id]
    deadletter = _get_deadletter()
    deadletter[task_id] = {
        "error": error,
        "attempts": attempts,
        "failed_on": now,
    }
    logger.error(
        "Task %s dead-lettered after %s attempts: %s"
        % (task_id, attempts, error))
    return False
