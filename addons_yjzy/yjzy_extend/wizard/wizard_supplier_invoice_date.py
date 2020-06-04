# -*- coding: utf-8 -*-

from odoo import  fields, models, api, _
from odoo.exceptions import Warning



class wizard_supplier_invoice_date(models.TransientModel):
    _name = 'wizard.supplier.invoice_date'
    _description = u'更新供应商发票日期'

    line_ids = fields.One2many('wizard.supplier.invoice_date.line', 'wizard_id', 'Lines')


    def apply(self):
        for line in self.line_ids:
            line.invoice_id.date_finish = line.date
            line.invoice_id.purchase_date_finish_state = line.purchase_date_finish_state
            line.invoice_id.purchase_date_finish_att = line.purchase_date_finish_att





class wizard_supplier_invoice_date_line(models.TransientModel):
    _name = 'wizard.supplier.invoice_date.line'

    wizard_id = fields.Many2one('wizard.supplier.invoice_date', u'Wizard')
    invoice_id = fields.Many2one('account.invoice', u'发票')
    partner_id = fields.Many2one('res.partner', u'供应商', related='invoice_id.partner_id')
    date = fields.Date(u'日期')
    purchase_amount_total = fields.Monetary(u'采购应付金额', related='invoice_id.amount_total')
    currency_id = fields.Many2one('res.currency',u'币种',related='invoice_id.currency_id')
    purchase_date_finish_att = fields.Many2many('ir.attachment', string='供应商交单日附件')
    purchase_date_finish_state = fields.Selection([('draft',u'草稿'),('submit',u'待审批'),('done',u'完成')],'供应商交单审批状态')

    def action_purchase_date_finish_state_submit(self):
        for one in self:
            if not one.date:
                raise Warning('请先填写日期')
            if not one.purchase_date_finish_att :
                raise Warning('请提交附件')
            one.purchase_date_finish_state = 'submit'

    def action_purchase_date_finish_state_done(self):
        for one in self:
            one.purchase_date_finish_state = 'done'








