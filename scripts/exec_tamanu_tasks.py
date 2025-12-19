# -*- coding: utf-8 -*-

import argparse
import logging
import os
import sys

import transaction
from bes.lims.scripts import setup_script_environment
from bes.lims.tamanu import logger
from bes.lims.tamanu.tasks import queue
from bika.lims import api


__doc__ = """
Executes Tamanu-related tasks like notifications to Tamanu instance about
sample transitions and/or diagnostic reports
"""

parser = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument(
    "-m", "--max_tasks",
    help="Maximum tasks to be processed",
    default="10"
)
parser.add_argument(
    "-su", "--senaite_user",
    help="SENAITE user",
    default="tamanu"
)
parser.add_argument(
    "-v", "--verbose", action="store_true",
    help="Verbose logging"
)


def error(message, code=1):
    """Exit with error
    """
    print("ERROR: %s" % message)
    sys.exit(code)


def conflict_error(*args, **kwargs):
    """Exits with a conflict error
    """
    error("ConflictError: exhausted retries", code=os.EX_SOFTWARE)


def connection_error(message):
    """Exits with a connection error
    """
    error("ConnectionError: %s" % message, code=os.EX_UNAVAILABLE)


def main(app):
    args, _ = parser.parse_known_args()
    if hasattr(args, "help") and args.help:
        print("")
        parser.print_help()
        return parser.exit()

    username = args.senaite_user
    if not username:
        print("")
        parser.print_help()
        return parser.exit()

    # verbose logging
    log_mode = logging.DEBUG if args.verbose else logging.INFO
    logger.setLevel(log_mode)

    # Setup environment
    setup_script_environment(app, username=username, logger=logger)

    # do the work
    logger.info("-" * 79)
    logger.info("Executing Tamanu-specific tasks ...")

    # max number of tasks to process
    max_tasks = int(args.max_tasks)
    for num in range(0, max_tasks):
        task = queue.get()
        if not task:
            break

        task_name = task.__class__.__name__
        logger.info("%s: %s ..." % (task_name, api.get_path(task.context)))

        # try to process the task
        task.process()
        # do a transaction savepoint
        transaction.savepoint(optimistic=True)

    transaction.commit()
    logger.info("Executing Tamanu-specific tasks [DONE]")
    logger.info("-" * 79)


if __name__ == "__main__":
    main(app)  # noqa: F821
