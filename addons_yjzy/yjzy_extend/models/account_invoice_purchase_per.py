# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning, UserError
from .comm import invoice_attribute_all_in_one


class account_invoice(models.Model):
    _inherit = 'account.invoice'
    _description = '准备通过采购合同合并的账单'

    def create_account_invoice_purchases(self):
        account_invoice_purchases_obj = self.env['account.invoice.purchases']
        po_ids = self.invoice_line_ids.mapped('purchase_id')
        print('po_ids_akiny',po_ids)
        for po in po_ids:
            po_tb_amount = sum(x.price_subtotal for x in self.line_ids.filtered(lambda x: x.purchase_id == po))#出运采购金额

            account_invoice_purchases = account_invoice_purchases_obj.create({
                'tb_id': self.id,
                'po_id': po.id,

            })


class account_invoice_purchases(models.Model):
    _name = 'account.invoice.purchases'
    _description = '账单通过采购单合并明细'

    po_id = fields.Many2one('purchase.order','Purchase')
    po_currency_id = fields.Many2one('res.currency','采购货币',default=lambda self: self.env.user.company_id.currency_id)
    po_tb_amount = fields.Monetary('出运采购金额',currency_field='po_currency_id')
