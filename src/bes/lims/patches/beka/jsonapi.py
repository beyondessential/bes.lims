# -*- coding: utf-8 -*-

import traceback

import json
import six
import sys
from bika.lims import api
from bika.lims.utils import to_utf8
from plone.app.textfield import RichTextValue


def load_field_values(instance, include_fields):
    """Load values from an AT object schema fields into a list of dictionaries
    """
    # TODO AT/Dexterity support. Refactor all this
    ret = {}
    val = None
    fields = api.get_fields(instance)
    for fieldname, field in fields.items():
        if include_fields and fieldname not in include_fields:
            continue
        try:
            val = field.get(instance)
        except AttributeError:
            # If this error is raised, make a look to the add-on content
            # expressions used to obtain their data.
            print("AttributeError:", sys.exc_info()[1])
            print("Unreachable object. Maybe the object comes from an Add-on")
            print(traceback.format_exc())

        if isinstance(val, RichTextValue):
            val = val.raw

        if val and not api.is_dexterity_content(instance):
            field_type = field.type
            # If it a proxy field, we should know to the type of the proxied
            # field
            if field_type == 'proxy':
                actual_field = field.get_proxy(instance)
                field_type = actual_field.type
            if field_type == "blob" or field_type == 'file':
                continue
            # I put the UID of all references here in *_uid.
            if field_type in ['reference', 'uidreference']:
                if type(val) in (list, tuple):
                    ret[fieldname + "_uid"] = [v.UID() for v in val]
                    val = [to_utf8(v.Title()) for v in val]
                else:
                    ret[fieldname + "_uid"] = val.UID()
                    val = val.Title()
            elif field_type == 'boolean':
                val = True if val else False

        if val and isinstance(val, six.string_types):
            val = to_utf8(val)

        if api.is_object(val):
            ret[fieldname + "_uid"] = api.get_uid(val)
            val = api.get_title(val)

        try:
            json.dumps(val)
        except Exception:
            val = str(val)
        ret[fieldname] = val
    return ret
