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

import logging
import os

from AccessControl.SecurityManagement import newSecurityManager
from bes.lims import logger as DEFAULT_LOGGER
from senaite.core.scripts.utils import setup_site
from Zope2 import configure


def get_zope_conf():
    """Returns the zope configuration that better suits with current execution
    process. Raises an exception if no suitable zope config is found
    """
    cwd = os.getcwd()
    lookup_paths = [
        os.path.join(cwd, "parts/client_reserved/etc/zope.conf"),
        os.path.join(cwd, "parts/client_99_reserved/etc/zope.conf"),
        os.path.join(cwd, "parts/client1/etc/zope.conf"),
        os.path.join(cwd, "parts/instance/etc/zope.conf"),
    ]
    for path in lookup_paths:
        if os.path.exists(path):
            return path

    raise Exception("Could not find zope.conf in {}".format(lookup_paths))


def setup_script_environment(app, stream_out=False, username="admin",
                             logger=DEFAULT_LOGGER):
    """Setup the suitable environment for running scripts from terminal
    """
    # Load zope configuration
    zope_conf = get_zope_conf()
    configure(zope_conf)

    # Verbose logging
    logger.setLevel(logging.DEBUG)
    if stream_out:
        logger.addHandler(logging.StreamHandler())

    # Load site
    site = app.senaite
    setup_site(site)

    # Login as superuser
    user = app.acl_users.getUser(username)
    if not user:
        # try with users from site
        user = site.acl_users.getUser(username)

    newSecurityManager(None, user.__of__(app.acl_users))
