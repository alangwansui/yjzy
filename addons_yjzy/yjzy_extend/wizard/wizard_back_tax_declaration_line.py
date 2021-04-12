# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning


class WizardBackTaxDeclaration(models.TransientModel):
    _name = 'wizard.back.tax.declaration'



    gongsi_id = fields.Many2one('gongsi', '内部公司')

    invoice_ids = fields.Many2many('account.invoice', 'ref_inv_btd', 'inv_id', 'btd_id', u'账单')

    def apply(self):
        ctx = self.env.context
        btd_id = ctx.get('active_id')
        invoice_ids = self.invoice_ids
        btd_line_obj = self.env['back.tax.declaration.line']
        for inv in invoice_ids:
            btd_line = btd_line_obj.create({
                'btd_id':btd_id,
                'invoice_id':inv.id,

            })

        return True

#####################################################################################################################
