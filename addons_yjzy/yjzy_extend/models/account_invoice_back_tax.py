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

    def compute_real_invoice_auto_state_1_2(self):
        for one in self:
            real_invoice_auto = one.real_invoice_auto
            if one.real_invoice_auto:
                real_invoice_auto_state_1 = real_invoice_auto.state_1
                real_invoice_auto_state_2 = real_invoice_auto.state_2
            else:
                real_invoice_auto_state_1 = False
                real_invoice_auto_state_2 = False
            one.real_invoice_auto_state_1 = real_invoice_auto_state_1
            one.real_invoice_auto_state_1 = real_invoice_auto_state_2


    purchase_invoice_ids = fields.Many2many('account.invoice',compute=compute_purchase_invoice_ids)

    real_invoice_auto = fields.Many2one('real.invoice.auto',)

    real_invoice_auto_state_1 = fields.Selection(
        [('10', '报关数据待锁定'), ('20', '报关数据已锁定-应收发票待锁定'), ('30', '应收发票锁定-发票未收齐'), ('40', '发票已收齐-未开销项'),
         ('50', '已开销项-未申报退税'), ('60', '已申报退税未收退税'), ('70','已收退税')],compute=compute_real_invoice_auto_state_1_2,store=True)
    real_invoice_auto_state_2 = fields.Selection(
        [('10', '正常待锁定.'), ('20', '异常待锁定.'), ('30', '正常待锁定'), ('40', '异常待锁定'), ('50', '正常未收齐'),
         ('60', '异常未收齐'), ('70', '正常未开'), ('75', '异常未开'), ('80', '正常未申报'), ('90', '异常未申报'), ('100', '正常未收'),('110','异常未收'),('120','已收退税')],
        compute=compute_real_invoice_auto_state_1_2,store=True)


