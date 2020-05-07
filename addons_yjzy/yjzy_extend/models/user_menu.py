# -*- coding: utf-8 -*-
import pytz
from datetime import datetime, timedelta, date
from odoo.exceptions import Warning
from odoo.tools.safe_eval import safe_eval
from odoo import models, fields, api
from jinja2 import Template
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
import logging
from dateutil import relativedelta


class user_menu(models.Model):
    _inherit = 'user.menu'

    hr_expense_ids = fields.One2many('hr.expense', 'user_menu_id', string='费用明细')
    hr_expense_payment_ids = fields.One2many('hr.expense',compute='compute_hr_expense',  string='费用明细')
    hr_expense_approve_un_payment_ids = fields.One2many('hr.expense',compute='compute_hr_expense', string='费用明细')  #domain=[('payment_date','>',context_today().strftime('%Y-01-01 00:00:00'))],
    hr_expense_submit_ids = fields.One2many('hr.expense', compute='compute_hr_expense', group_by='',string='费用明细')
    hr_expense_draft_ids = fields.One2many('hr.expense', compute='compute_hr_expense', string='费用明细')

    @api.one
    def compute_hr_expense(self):
        now = fields.datetime.now()
        month = now.strftime('%Y-%m-01 00:00:00')
        year = now.strftime('%Y-01-01 00:00:00')
        for one in self:
           hr_expense_payment_ids = one.hr_expense_ids.filtered(
           lambda x: x.payment_date and x.payment_date > year and x.state in ('done') and x.total_amount > 0 and (x.categ_id != 193 or x.categ_id == False))
           one.hr_expense_payment_ids = hr_expense_payment_ids

           hr_expense_approve_un_payment_ids = one.hr_expense_ids.filtered(
           lambda x: x.state in ('confirmed') and x.total_amount > 0 and (x.categ_id != 193 or x.categ_id == False))
           one.hr_expense_approve_un_payment_ids = hr_expense_approve_un_payment_ids

           hr_expense_submit_ids = one.hr_expense_ids.filtered(
               lambda x: x.state in ('submit','approval','employee_approval','account_approval','manager_approval') and x.total_amount > 0 and (x.categ_id != 193 or x.categ_id == False))
           one.hr_expense_submit_ids = hr_expense_submit_ids

           hr_expense_draft_ids = one.hr_expense_ids.filtered(
               lambda x: x.sheet_state in ('draft','cancel') and x.total_amount > 0 and (
                                     x.categ_id != 193 or x.categ_id == False))
           one.hr_expense_draft_ids = hr_expense_draft_ids