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



class wizard_supplier_invoice_date_line(models.TransientModel):
    _name = 'wizard.supplier.invoice_date.line'

    wizard_id = fields.Many2one('wizard.supplier.invoice_date', u'Wizard')
    invoice_id = fields.Many2one('account.invoice', u'发票')
    partner_id = fields.Many2one('res.partner', u'供应商', related='invoice_id.partner_id')
    date = fields.Date(u'日期')












