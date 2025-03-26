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

from senaite.core.interfaces import IGetStickerTemplates
from senaite.core.vocabularies.stickers import get_sticker_templates
from zope.interface import implementer


@implementer(IGetStickerTemplates)
class StickerTemplates(object):
    """
    Adapter that returns a list of barcode stickers associated with products
    that do not belong to senaite namespace. If the current instance does not
    have barcode stickers registered other than those from senaite namespace,
    the adapter returns all barcode sticker templates registered, regardless
    of the namespace.

    Each item in the returned list is a dict with the following structure:

        {
            "id": <template_id>,        # Unique identifier for the template
            "title": <template_title>,  # Descriptive title of the template
            "selected": True/False,     # False
        }
    """

    def __init__(self, context):
        self.context = context

    def __call__(self, request):
        """Returns the templates that do not belong to senaite namespace
        """
        # get all templates
        templates = get_sticker_templates()

        # purge those from senaite namespace
        templates = filter(lambda tp: not self.is_from_senaite(tp), templates)

        # skip auto-selection of template
        for template in templates:
            template["selected"] = False
        return templates

    def is_from_senaite(self, template):
        """Returns whether this template is from senaite namespace
        """
        template_id = template.get("id")
        if ":" not in template_id:
            # ids from senaite.core come without prefix
            return True
        return template_id.startswith("senaite.")
