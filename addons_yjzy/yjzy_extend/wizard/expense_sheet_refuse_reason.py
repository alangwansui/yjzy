# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ExpenseSheetRefuseWizard(models.TransientModel):
    """This wizard can be launched from an he.expense (an expense line)
    or from an hr.expense.sheet (En expense report)
    'hr_expense_refuse_model' must be passed in the context to differentiate
    the right model to use.
    """

    _name = "expense.sheet.refuse.wizard"
    _description = "Expense Refuse Reason Wizard"

    reason = fields.Char(string='Reason', required=True)
    expense_sheet_id = fields.Many2one('hr.expense.sheet')

    #取得当前的活动id
    @api.model
    def default_get(self, fields):
        res = super(ExpenseSheetRefuseWizard, self).default_get(fields)
        active_ids = self.env.context.get('active_ids', [])
        res.update({
            'expense_sheet_id': active_ids[0] if active_ids else False,
            })
        return res
    #写上拒绝的理由，sale_order上执行拒绝
    def expense_sheet_refuse_reason(self):
        self.ensure_one()
        self.expense_sheet_id.action_refuse(self.reason)
        return {'type': 'ir.actions.act_window_close'}

    def expense_sheet_refuse_reason_to_account(self):
        self.ensure_one()
        self.expense_sheet_id.action_refuse_to_account(self.reason)
        return {'type': 'ir.actions.act_window_close'}
