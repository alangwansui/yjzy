# -*- coding: utf-8 -*-
from num2words import num2words
from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning


class transport_bill(models.Model):
    _inherit = 'transport.bill'

    plan_invoice_auto_ids = fields.One2many('plan.invoice.auto','bill_id','应收发票')
    real_invocie_auto_ids = fields.One2many('real.invoice.auto','bill_id','实际发票')