# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning


class wizard_pre_advance(models.TransientModel):
    _name = 'wizard.pre.advance'
    _description = '添加本次预收预付认领明细'

    pre_advance_line = fields.Many2one('pre.advance','预收预付明细')
    payment_advance_id = fields.Many2one('account.payment','预收预付款单')
    is_selected = fields.Boolean('是否选中')



    def apply(self):
        self.ensure_one()
        self.payment_advance_id.pre_advance_id = self.pre_advance_line
        self.pre_advance_line.is_selected = True
        self.payment_advance_id.is_pre_advance_line = True
        return True

    def cancel(self):
        self.ensure_one()
        self.payment_advance_id.pre_advance_id = False
        self.pre_advance_line.is_selected = False
        self.payment_advance_id.is_pre_advance_line = False
        return True




