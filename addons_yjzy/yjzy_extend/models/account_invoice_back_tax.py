# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning, UserError
from .comm import invoice_attribute_all_in_one



class account_invoice(models.Model):
    _inherit = 'account.invoice'




    purchase_invoice_ids = fields.Many2many('account.invoice')


