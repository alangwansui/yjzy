# © 2017 Nedas Žilinskas <nedas.zilinskas@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.http import request
from odoo import api, fields, models


class ForumForum(models.Model):

    _inherit = 'forum.forum'

    restricted_partner_category_ids = fields.Many2many(
        comodel_name='res.partner.hcategory',
        string='Restrict to Partner Categories',
    )

    forum_denied_page_id = fields.Many2one(
        comodel_name='website.page',
        string='Forum access denied page',
    )

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}

        if 'website_id' in context:
            cat = request.env.user.partner_id.allowed_forum_ids
            args += [('id', 'in', cat.ids)]

        return super(ForumForum, self).search(
            args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
        )
