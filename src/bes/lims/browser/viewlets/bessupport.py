# -*- coding: utf-8 -*-

from plone import api as ploneapi
from plone.app.layout.viewlets import ViewletBase
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile


class BESSupportViewlet(ViewletBase):
    """Renders the script that displays the Zendesk's icon at bottom-left
    """
    index = ViewPageTemplateFile("templates/bessupport.pt")

    def is_visible(self):
        """Returns whether the viewlet is visible or not
        """
        if "localhost" in self.request.get("HTTP_HOST"):
            return False
        return not ploneapi.user.is_anonymous()
