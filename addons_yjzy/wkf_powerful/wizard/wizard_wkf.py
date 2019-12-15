# -*- coding: utf-8 -*-
##############################################################################

from odoo import api, fields, models, _


class wizard_wkf_message(models.TransientModel):
    _name = 'wizard.wkf.message'
    name = fields.Char(u'Note')

    @api.multi
    def apply(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx.update({'wizard_message': self.name})

        order = self.env[ctx.get('active_model')].browse(ctx.get('active_id'))
        order.with_context(ctx).wkf_action(self.name)
        return True





