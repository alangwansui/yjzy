# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class TransportRefuseWizard(models.TransientModel):
    """This wizard can be launched from an he.expense (an expense line)
    or from an hr.expense.sheet (En expense report)
    'hr_expense_refuse_model' must be passed in the context to differentiate
    the right model to use.
    """

    _name = "transport.refuse.wizard"
    _description = "Transport Refuse Reason Wizard"

    reason = fields.Char(string='Reason', required=True)
    tb_id = fields.Many2one('transport.bill')

    #取得当前的活动id
    @api.model
    def default_get(self, fields):
        res = super(TransportRefuseWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids', [])
        res.update({
            'tb_id': active_ids[0] if active_ids else False,
            })
        return res
    #写上拒绝的理由，sale_order上执行拒绝
    def transport_refuse_reason(self):
        self.ensure_one()
        self.tb_id.action_refuse(self.reason)
        return {'type': 'ir.actions.act_window_close'}
