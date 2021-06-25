# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from datetime import datetime


class ManualCompleteRealInvoiceWizard(models.TransientModel):
    """This wizard can be launched from an he.expense (an expense line)
    or from an hr.expense.sheet (En expense report)
    'hr_expense_refuse_model' must be passed in the context to differentiate
    the right model to use.
    """

    _name = "manual.complete.real.invoice.wizard"
    _description = "Manuel Complete Real Invoice Wizard"

    reason = fields.Char(string='Reason', required=True)
    pia_id = fields.Many2one('plan.invoice.auto')

    #取得当前的活动id
    @api.model
    def default_get(self, fields):
        res = super(ManualCompleteRealInvoiceWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids', [])
        res.update({
            'pia_id': active_ids[0] if active_ids else False,
            })
        return res

    def manual_complete_real_invoice(self):
        self.ensure_one()
        self.pia_id.manual_complete_real_invoice_comments = self.reason
        self.pia_id.manual_complete_real_invoice_uid = self.env.user
        self.pia_id.manual_complete_real_invoice_date = datetime.today()
        self.pia_id.action_complete_real_invoice(self.reason)
        return {'type': 'ir.actions.act_window_close'}


