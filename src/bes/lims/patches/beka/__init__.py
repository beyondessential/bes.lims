# -*- coding: utf-8 -*-

from bika.lims import jsonapi as _jsonapi
from .jsonapi import load_field_values

# https://pypi.org/project/collective.monkeypatcher/#patching-module-level-functions
_jsonapi.load_field_values = load_field_values
