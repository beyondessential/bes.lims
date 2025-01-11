# -*- coding: utf-8 -*-

from bes.lims import PRODUCT_NAME
from senaite.core.i18n import translate as core_translate


def translate(msgid, **kwargs):
    """Translate any zope i18n msgid returned from MessageFactory
    """
    domain = kwargs.pop("domain", PRODUCT_NAME)
    return core_translate(msgid, domain=domain, **kwargs)
