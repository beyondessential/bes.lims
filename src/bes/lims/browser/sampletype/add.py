# -*- coding: utf-8 -*-

import copy

from senaite.core.browser.dexterity.add import DefaultAddForm
from senaite.core.browser.dexterity.add import DefaultAddView


class SampleTypeAddForm(DefaultAddForm):
    """Sample Type add view
    """
    portal_type = "SampleType"

    def updateFieldsFromSchemata(self):
        """see plone.autoform.base.AutoFields
        """
        super(SampleTypeAddForm, self).updateFieldsFromSchemata()

        # Make the min volume field non-required
        # Schema fields are shared between instances by default, so we need to
        # create a copy of it
        min_vol = self.fields["min_volume"]
        min_vol_field = copy.copy(min_vol.field)
        min_vol_field.required = False
        min_vol.field = min_vol_field


class SampleTypeAddView(DefaultAddView):
    form = SampleTypeAddForm
