# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp


class wizard_transport4so(models.TransientModel):
    _name = 'wizard.tb.po.invoice.tax'



    tb_po_id =fields.Many2one('tb.po.invoice',u'账单申请单')

    def apply_submit_with_out_tax(self):

        self.tb_po_id.action_submit()



#####################################################################################################################
