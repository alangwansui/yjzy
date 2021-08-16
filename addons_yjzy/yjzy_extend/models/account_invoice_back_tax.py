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

    @api.depends('real_invoice_auto','real_invoice_auto.state_1','real_invoice_auto.state_2')
    def compute_real_invoice_auto_state_1_2(self):
        for one in self:
            real_invoice_auto = one.real_invoice_auto
            if one.real_invoice_auto:
                real_invoice_auto_state_1 = real_invoice_auto.state_1
                real_invoice_auto_state_2 = real_invoice_auto.state_2
            else:
                real_invoice_auto_state_1 = '10'
                real_invoice_auto_state_2 = '10'
            one.real_invoice_auto_state_1 = real_invoice_auto_state_1
            one.real_invoice_auto_state_2 = real_invoice_auto_state_2

    def _default_name(self):
        line_name = self.env['ir.sequence'].next_by_code('back.tax.declaration.line.name')
        return line_name

    purchase_invoice_ids = fields.Many2many('account.invoice',compute=compute_purchase_invoice_ids)

    real_invoice_auto = fields.Many2one('plan.invoice.auto',u'应收发票')

    real_invoice_auto_state_1 = fields.Selection(
        [('10', '报关数据待锁定'), ('20', '报关数据已锁定-应收发票待锁定'), ('30', '应收发票锁定-发票未收齐'), ('40', '发票已收齐-未开销项'),
         ('50', '已开销项-未申报退税'), ('60', '已申报退税未收退税'), ('70','已收退税')],index=True,compute=compute_real_invoice_auto_state_1_2,store=True)
    real_invoice_auto_state_2 = fields.Selection(
        [('10', '正常待锁定.'), ('20', '异常待锁定.'), ('30', '正常待锁定'), ('40', '异常待锁定'), ('50', '正常未收齐'),
         ('60', '异常未收齐'), ('70', '正常未开'), ('75', '异常未开'), ('80', '正常未申报'), ('90', '异常未申报'), ('100', '正常未收'),('110','异常未收'),('120','已收退税')],
        index=True,compute=compute_real_invoice_auto_state_1_2,store=True)

    adjustment_invoice_id = fields.Many2one('account.invoice',u'退税申报调节账单')
    is_adjustment = fields.Boolean(u'是否被调节', defualt=False)

    adjustment_invoice_origin_id = fields.Many2one('account.invoice',u'调节账单对应原始账单')

    line_name = fields.Char(u'账单排序编号', default=lambda self: self._default_name())

    df_all_in_one_invoice_id = fields.Many2one('back.tax.declaration', u'报关申报表')
    btd_line_all_in_one_invoice_ids = fields.One2many('back.tax.declaration.line', 'back_tax_all_in_one_invoice', u'申报明细')
    back_tax_declaration_out_refund_invoice_id = fields.Many2one('account.invoice', u'整体系统内认领反向发票')
    back_tax_declaration_invoice_ids = fields.One2many('back.tax.declaration', 'back_tax_all_in_one_invoice_id', u'退税申报')
    declaration_title = fields.Char(u'申报说明', related='df_all_in_one_invoice_id.declaration_title')
    declaration_date = fields.Date(u'申报日期', related='df_all_in_one_invoice_id.declaration_date')
    declaration_amount_all = fields.Monetary(u'本次申报金额', currency_field='currency_id',
                                             related='df_all_in_one_invoice_id.declaration_amount_all')
    back_tax_declaration_name = fields.Char(u'编号', related='df_all_in_one_invoice_id.name', store=True)
    declaration_state = fields.Selection(
        [('draft', u'草稿'), ('approval', '审批中'), ('done', u'确认'), ('paid', u'已收款'), ('cancel', u'取消')], 'State',
        related='df_all_in_one_invoice_id.state')