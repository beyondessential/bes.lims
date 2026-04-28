# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# Import a local FHIR Bundle JSON file into SENAITE.
#
# Usage (inside Zope/SENAITE):
#   bin/instance run import_bundle.py -f /path/to/bundle.json
#   bin/instance run import_bundle.py -f /path/to/bundle.json --dry

import argparse
import io
import json
import logging
import sys
from datetime import datetime, timedelta
from time import time

from bes.lims.tamanu.resources.bundle import BundleResource
from bes.lims.tamanu.importer import BundleImporter

logger = logging.getLogger("import_bundle")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawTextHelpFormatter,
)
parser.add_argument("-f", "--file", required=True,
                    help="Path to the FHIR Bundle JSON file")
parser.add_argument("-su", "--senaite_user", default="admin",
                    help="SENAITE username to run as (default: admin)")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Verbose (DEBUG) logging")
parser.add_argument("-d", "--dry", action="store_true",
                    help="Dry run: log what would happen, do NOT write to SENAITE")


def load_bundle(path):
    try:
        with io.open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (IOError, OSError) as e:
        logger.error("Cannot open file: %s" % e)
        sys.exit(1)
    except ValueError as e:
        logger.error("Invalid JSON: %s" % e)
        sys.exit(1)

    if data.get("resourceType") != "Bundle":
        logger.error("Not a FHIR Bundle (resourceType != 'Bundle')")
        sys.exit(1)

    bundle = BundleResource(data)
    logger.info("Bundle loaded - {0} entries, type={1}".format(
        len(data.get("entry", [])), bundle.bundle_type))
    return bundle


def main(app):  # noqa: F841 - app injected by Zope bin/instance run
    args, _ = parser.parse_known_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    from bes.lims.scripts import setup_script_environment
    setup_script_environment(app, username=args.senaite_user, logger=logger)
    logging.getLogger("bes.lims.tamanu").setLevel(logging.INFO)
    mode = "DRY RUN" if args.dry else "LIVE"
    logger.info("=" * 60)
    logger.info("import_bundle.py  [{0}]".format(mode))
    logger.info("File   : {0}".format(args.file))
    logger.info("Started: {0}".format(datetime.now().isoformat()))
    logger.info("=" * 60)

    start = time()
    bundle = load_bundle(args.file)
    BundleImporter(bundle).run(dry_run=args.dry)
    logger.info("Elapsed: {0}".format(timedelta(seconds=(time() - start))))
    logger.info("=" * 60)


if __name__ == "__main__":
    main(app)  # noqa: F821
