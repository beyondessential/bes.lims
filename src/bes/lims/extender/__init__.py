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

from bes.lims import logger


def update_field(schema, field_id, field_info):
    """Updates the schema field for with the field_info provided
    """
    # Field properties
    field = schema[field_id]
    field.schemata = field_info.get("schemata", field.schemata)
    props = filter(lambda f: f != "widget", field_info.keys())
    for prop_id in props:
        if not hasattr(field, prop_id):
            logger.warn("Field property {} is missing".format(prop_id))
            continue
        setattr(field, prop_id, field_info.get(prop_id))
        if prop_id in ["validators", "subfield_validators"]:
            # Resolve validators in the service
            if hasattr(field, "_validationLayer"):
                field._validationLayer()

    # Widget properties
    widget = field.widget
    props = field_info.get("widget", {})
    if isinstance(props, dict):
        for prop_id, prop_value in props.items():
            if not hasattr(widget, prop_id):
                logger.warn("Widget Property {} is missing".format(prop_id))
                continue
            setattr(widget, prop_id, prop_value)
    elif props:
        field.widget = props
