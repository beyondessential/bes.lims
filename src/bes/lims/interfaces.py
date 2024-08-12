# -*- coding: utf-8 -*-
#
# This file is part of BES.LIMS.
#
# Copyright 2024 Beyond Essential Systems Pty Ltd

from senaite.ast import ISenaiteASTLayer
from senaite.core.interfaces import ISenaiteCore
from senaite.impress.interfaces import ILayer as ISenaiteImpressLayer
from senaite.lims.interfaces import ISenaiteLIMS
from senaite.patient import ISenaitePatientLayer


class IBESLimsLayer(ISenaiteCore,
                    ISenaiteLIMS,
                    ISenaiteImpressLayer,
                    ISenaiteASTLayer,
                    ISenaitePatientLayer):
    """Zope 3 browser Layer interface specific for bes.lims
    This interface is referred in profiles/default/browserlayer.xml.
    All views and viewlets register against this layer will appear in the site
    only when the add-on installer has been run.
    """
