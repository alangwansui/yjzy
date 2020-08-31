# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp
from lxml import etree

class DeclareDeclaration(models.Model):
    _name = 'declare.declaration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '报关申报表'
    _order = 'id desc'

    def compute_info(self):
        invoice_back_tax_ids = self.invoice_back_tax_ids
        amount_all = sum(x.amount_total for x in invoice_back_tax_ids)
        amount_residual = sum(x.residual_signed for x in invoice_back_tax_ids)
        self.amount_all = amount_all
        self.amount_residual = amount_residual

    name = fields.Char('编号', default=lambda self: self.env['ir.sequence'].next_by_code('declare.declaration'))
    invoice_back_tax_ids = fields.One2many('account.invoice','df_id',u'退税发票')
    state = fields.Selection([('draft',u'草稿'),('done',u'确认'),('cancel',u'取消')],'State')
    amount_all = fields.Float(u'退税总金额',compute=compute_info)
    amount_residual = fields.Float(u'未收退税总金额',compute=compute_info)









#####################################################################################################################
