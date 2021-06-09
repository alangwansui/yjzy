# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp


class WizardTbPoInvoiceNew(models.TransientModel):
    _name = 'wizard.tb.po.invoice.new'

    def compute_tb_po_expense(self):
        for one in self:
            one.tb_po_expense = self.env['tb.po.invoice'].search([('state','=','25')])


    tb_id = fields.Many2one('transport.bill', u'出运单')
    tb_po_id = fields.Many2one('tb.po.invoice',)#default=lambda self: self.tb_id.create_tb_po_invoice()
    wizard_tb_po_invoice_line_new = fields.One2many('wizard.tb.po.invoice.line.new','wizard_tb_po_invoice')


    def apply(self):
        wizard_tb_po_invoice_line_new = self.wizard_tb_po_invoice_line_new
        wizard_tb_po_invoice_line_claim_new = self.wizard_tb_po_invoice_line_new.filtered(lambda x: x.is_claim == False)
        wizard_tb_po_invoice_line_claim_id = self.wizard_tb_po_invoice_line_new.filtered(lambda x: x.is_claim == True)
        view = self.env.ref('yjzy_extend.tb_po_form')
        if len(wizard_tb_po_invoice_line_claim_id) > 1:
            raise Warning('选择的费用转货款认领单大于1')
        elif len(wizard_tb_po_invoice_line_new) == len(wizard_tb_po_invoice_line_claim_new):
            self.tb_po_id = self.tb_id.create_tb_po_invoice()
            return {
                'name': 'test',
                'view_type': 'tree,form',
                "view_mode": 'form',
                'res_model': 'tb.po.invoice',
                'type': 'ir.actions.act_window',
                'view_id': view.id,
                'target': 'current',
                'res_id': self.tb_po_id.id,
                'context': {}
            }
        else:
            tb_po_id = wizard_tb_po_invoice_line_claim_id.tb_po_expense
            tb_po_id.tb_id = self.tb_id
            tb_po_id.onchange_tb_id()
            return {
                'name': 'test',
                'view_type': 'tree,form',
                "view_mode": 'form',
                'res_model': 'tb.po.invoice',
                'type': 'ir.actions.act_window',
                'view_id': view.id,
                'target': 'current',
                'res_id': tb_po_id.id,
                'context': {}
            }




class WizardTbPoInvoiceLineNew(models.TransientModel):
    _name = 'wizard.tb.po.invoice.line.new'

    wizard_tb_po_invoice = fields.Many2one('wizard.tb.po.invoice.new')
    tb_po_expense = fields.Many2one('tb.po.invoice','费用转货款')
    is_claim = fields.Boolean('是否认领',default = False)








#####################################################################################################################
