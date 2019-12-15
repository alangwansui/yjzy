# © 2017 Nedas Žilinskas <nedas.zilinskas@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import werkzeug
from odoo.http import request
from odoo.addons.website_forum.controllers.main import WebsiteForum


class Main(WebsiteForum):

    def _prepare_forum_values(self, forum=None, **kwargs):
        if forum and forum not in request.env.user.partner_id.allowed_forum_ids:
            raise werkzeug.exceptions.NotFound()

        return super(Main, self)._prepare_forum_values(
            forum=forum,
            kwargs=kwargs,
        )
