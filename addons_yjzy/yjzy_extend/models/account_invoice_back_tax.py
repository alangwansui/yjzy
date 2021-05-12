# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning, UserError
from .comm import invoice_attribute_all_in_one



class account_invoice(models.Model):
    _inherit = 'account.invoice'


    def compute_purchase_invoice_ids(self):
        for one in self:
            one.purchase_invoice_ids = one.bill_id.all_purchase_invoice_ids

    purchase_invoice_ids = fields.Many2many('account.invoice',compute=compute_purchase_invoice_ids)

    real_invoice_auto = fields.Many2one('real.invoice.auto',)


