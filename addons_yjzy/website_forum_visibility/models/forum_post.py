# © 2017 Nedas Žilinskas <nedas.zilinskas@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.http import request
from odoo import api, models


class ForumPost(models.Model):

    _inherit = 'forum.post'

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        context = self._context or {}

        if 'website_id' in context:
            cat = request.env.user.partner_id.allowed_forum_ids
            args += [('forum_id', 'in', cat.ids)]

        return super(ForumPost, self).search(
            args,
            offset=offset,
            limit=limit,
            order=order,
            count=count,
        )

    def _get_post_karma_rights(self):
        res = super(ForumPost, self)._get_post_karma_rights()

        for rec in self:
            if rec.forum_id.id not in \
               request.env.user.partner_id.allowed_forum_ids.ids:
                rec.can_view = False

        return res
