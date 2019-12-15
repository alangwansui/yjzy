# © 2017 Nedas Žilinskas <nedas.zilinskas@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re
from odoo.http import request
from odoo import models


class IRHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _serve_404(cls):
        req_page = request.httprequest.path

        if req_page.find('/forum/') > -1:
            bid = re.search(r'\/forum\/[a-zA-Z0-9-]+([0-9]+)', req_page).group(1)
            if bid:
                custom_404 = request.env['forum.forum'].sudo().browse(
                    int(bid)
                ).forum_denied_page_id
                if custom_404:
                    return request.render(custom_404.key, {'path': req_page[1:]})

        return super(IRHttp, cls)._serve_404()
