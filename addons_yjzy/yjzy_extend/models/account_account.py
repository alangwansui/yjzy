# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import Warning


class account_account(models.Model):
    _inherit = 'account.account'

    polarity = fields.Selection([(0, u'无'), (1, u'借方'), (-1, u'贷方')], u'借/贷', defualt=0)

    def get_balance(self):
        self.ensure_one()
        lines = self.env['account.move.line'].search([('account_id', '=', self.id)])
        balance, foreign_balance, rate = 0, 0, 0
        balance = sum([x.debit - x.credit for x in lines])
        foreign_balance = sum([x.amount_currency for x in lines])
        rate = balance != 0 and foreign_balance / balance or 0

        return balance, foreign_balance, rate

    def button_test_balnace(self):
        balance, foreign_balance, ratio = self.get_balance()
        raise Warning('本币%s 外币%s 平均汇率%s' % (balance, foreign_balance, ratio))
