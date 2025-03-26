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


from senaite.core.vocabularies.stickers import get_sticker_templates
from senaite.core.schema.vocabulary import to_simple_vocabulary


def call(self, context, filter_by_type=False):
    templates = get_sticker_templates(filter_by_type=filter_by_type)

    # purge templates from core (come without prefix followed by ':')
    other = filter(lambda tp: ":" in tp.get("id"), templates)
    core = filter(lambda tp: tp not in other, templates)

    # if there are no product-specific templates, fallback to core's
    templates = other if other else core

    return to_simple_vocabulary([(t["id"], t["title"]) for t in templates])
