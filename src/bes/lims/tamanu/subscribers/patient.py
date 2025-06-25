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

from Products.CMFCore.permissions import ModifyPortalContent
from bes.lims.tamanu.config import TAMANU_USER
from bika.lims.api import security as sapi
from bika.lims.api import user as uapi


def on_patient_added(instance, event):
    """Grant Owner for user 'tamanu' role and revoke ModifyPortalContent
    permission for Patient objects created by user 'tamanu', for all
    users but 'tamanu'.
    """
    if uapi.get_user_id() != TAMANU_USER:
        # user creating the patient is not tamanu's, do nothing
        return

    # don't allow the edition, but to tamanu (Owner) only
    sapi.manage_permission_for(instance, ModifyPortalContent, ["Owner"])

    # re-index object security indexes (e.g. allowedRolesAndUsers)
    instance.reindexObjectSecurity()


def on_patient_modified(instance, event):
    """Grant Owner for user 'tamanu' role and revoke ModifyPortalContent
    permission for Patient objects modified by user 'tamanu', for all
    users but 'tamanu'.
    """
    user_id = uapi.get_user_id()
    if user_id != TAMANU_USER:
        # user modifying the patient is not tamanu's, do nothing
        return

    # revoke 'Owner' roles to the creator to prevent further edits
    creator = instance.Creator()
    if creator != TAMANU_USER:
        sapi.revoke_local_roles_for(instance, roles=["Owner"], user=creator)

    # grant 'Owner' role to the user who is modifying the object
    sapi.grant_local_roles_for(instance, roles=["Owner"], user=user_id)

    # don't allow the edition, but to tamanu (Owner) only
    sapi.manage_permission_for(instance, ModifyPortalContent, ["Owner"])

    # re-index object security indexes (e.g. allowedRolesAndUsers)
    instance.reindexObjectSecurity()
