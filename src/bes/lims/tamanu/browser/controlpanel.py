# -*- coding: utf-8 -*-

from bes.lims.tamanu import _
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.registry.interfaces import IRegistry
from plone.supermodel import model
from plone.z3cform import layout
from zope import schema
from zope.component import getUtility

PASSWORD_PLACEHOLDER = u"•" * 12


class ITamanuControlPanel(model.Schema):
    """Control panel settings for tamanu sync
    """

    host = schema.URI(
        title=_(
            u"title_tamanu_settings_host",
            default=u"Tamanu host"),
        description=_(
            u"description_tamanu_settings_host",
            default=u"Base URL of the Tamanu instance this LIMS syncs with. "
                    u"Used for all outbound requests targeting Tamanu "
                    u"resources previously imported into SENAITE."
        ),
        required=False,
    )

    email = schema.TextLine(
        title=_(
            u"title_tamanu_settings_email",
            default=u"Integration account email"),
        description=_(
            u"description_tamanu_settings_email",
            default=u"Email of the Tamanu account used by SENAITE to "
                    u"authenticate outbound requests."
        ),
        required=False,
    )

    password = schema.Password(
        title=_(
            u"title_tamanu_settings_password",
            default=u"Integration account password"),
        description=_(
            u"description_tamanu_settings_password",
            default=u"Password of the Tamanu account used by SENAITE to "
                    u"authenticate outbound requests."
        ),
        required=False,
    )

    create_clients_on_sync = schema.Bool(
        title=_(
            u"title_tamanu_settings_create_clients_on_sync",
            default=u"Create clients automatically during Tamanu sync"),
        description=_(
            u"description_tamanu_settings_create_clients_on_sync",
            default=u"If enabled, the Tamanu sync automatically creates a "
                    u"SENAITE client for each Encounter/ServiceProvider "
                    u"referenced by an incoming ServiceRequest when no "
                    u"counterpart exists yet. If disabled, ServiceRequests "
                    u"referencing unknown clients are skipped and must be "
                    u"resolved manually."
        ),
        default=False,
    )


class TamanuControlPanelForm(RegistryEditForm):
    schema = ITamanuControlPanel
    schema_prefix = "senaite.tamanu"
    label = _(
        u"controlpanel_tamanu",
        default=u"Tamanu Synchronization Settings"
    )

    def updateWidgets(self):
        super(TamanuControlPanelForm, self).updateWidgets()
        # The password widget's template intentionally never emits a `value`
        # attribute so the secret is not round-tripped to the browser. That
        # makes a configured password look identical to an unconfigured one.
        # Render dots as a placeholder when a password is stored, so admins
        # can tell at a glance that a value is set.
        pw_widget = self.widgets.get("password")
        if pw_widget is None:
            return
        registry = getUtility(IRegistry)
        if registry.get(self.schema_prefix + ".password"):
            pw_widget.placeholder = PASSWORD_PLACEHOLDER

    def applyChanges(self, data):
        # Treat an empty password submission as "do not change", so that
        # re-saving the form without retyping the password preserves the
        # stored value. To clear the password, unset it via the registry.
        if not data.get("password"):
            data.pop("password", None)
        return super(TamanuControlPanelForm, self).applyChanges(data)


TamanuControlPanelView = layout.wrap_form(
    TamanuControlPanelForm,
    ControlPanelFormWrapper
)
