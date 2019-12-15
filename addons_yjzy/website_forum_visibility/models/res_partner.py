# © 2017 Nedas Žilinskas <nedas.zilinskas@gmail.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResPartner(models.Model):

    _inherit = 'res.partner'

    allowed_forum_ids = fields.Many2many(
        comodel_name='forum.forum',
        compute='_compute_allowed_forum_ids',
    )

    def _compute_allowed_forum_ids(self):
        for rec in self:

            # get allowed categories for this partner category
            parent_id = rec
            while parent_id:
                partner = parent_id
                parent_id = parent_id.parent_id

            allowed_forum_ids = partner.hcategory_id.forum_ids.ids
            hparent_id = partner.hcategory_id.parent_id
            while hparent_id:
                allowed_forum_ids += hparent_id.forum_ids.ids
                hparent_id = hparent_id.parent_id
            allowed_forum_ids = list(set(allowed_forum_ids))

            allowed = self.env['forum.forum'].with_context({
                'in_website': False,
            }).search([
                '|',
                ('restricted_partner_category_ids', '=', False),
                ('id', 'in', allowed_forum_ids),
            ])

            # get disallowed categories for this partner category
            denied = self.env['forum.forum'].with_context({
                'in_website': False,
            }).search([
                ('restricted_partner_category_ids', '!=', False),
                ('id', 'not in', allowed.ids)
            ])

            rec.allowed_forum_ids = allowed - denied

    @api.multi
    def open_partner_category(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner.hcategory',
            'view_mode': 'form',
            'res_id': self.hcategory_id.id,
            'target': 'current',
            'flags': {'form': {'action_buttons': True}}
        }
