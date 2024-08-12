# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# Copyright 2024 Beyond Essential Systems Pty Ltd

import logging

from zope.i18nmessageid import MessageFactory

PRODUCT_NAME = "bes.lims"

messageFactory = MessageFactory(PRODUCT_NAME)
_ = messageFactory

logger = logging.getLogger(PRODUCT_NAME)


def initialize(context):
    """Initializer called when used as a Zope 2 product."""
    logger.info("*** Initializing BES LIMS Customization Package ***")
