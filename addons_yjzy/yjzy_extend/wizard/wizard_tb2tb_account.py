# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning


class wizard_tb2tb_account(models.TransientModel):
    _name = 'wizard.tb2tb.account'

    name = fields.Char(u'Name')

    @api.model
    def check(self, bills):
        pass
        # if len(bills.mapped('partner_id')) > 1:
        #     raise Warning(u'必须是同一个客户的出运记录')

    def apply(self):
        self.ensure_one()
        bill_ids = self._context.get('active_ids')
        bills = self.env['transport.bill'].browse(bill_ids)
        self.check(bills)
        tb_account = self.env['transport.bill.account'].create({
        })
        bills.write({'tba_id': tb_account.id})

        return {
            'name': u'出运报关金额',
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'transport.bill.account',
            'type': 'ir.actions.act_window',
            'res_id': tb_account.id,
            #'domain': [('id', '=', sale_cost)],
            # 'context': { },
        }











