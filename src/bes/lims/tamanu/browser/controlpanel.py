# -*- coding: utf-8 -*-

from bes.lims.tamanu import _
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.supermodel import model
from plone.z3cform import layout
from zope import schema


class ITamanuControlPanel(model.Schema):
    """Control panel settings for tamanu sync
    """

    create_clients_on_sync = schema.Bool(
        title=_("Create missing clients"),
        description=_(
            "Select this option for the Tamanu synchronization tool to "
            "automatically create counterpart clients for non-existing "
            "Encounter/ServiceProvider on ServiceRequest resources import."
        ),
        default=False,
    )


class TamanuControlPanelForm(RegistryEditForm):
    schema = ITamanuControlPanel
    schema_prefix = "senaite.tamanu"
    label = _(u"Tamanu Synchronization Settings")


TamanuControlPanelView = layout.wrap_form(
    TamanuControlPanelForm,
    ControlPanelFormWrapper
)
