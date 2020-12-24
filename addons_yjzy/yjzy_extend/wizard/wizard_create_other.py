# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp
from lxml import etree
from odoo.exceptions import UserError, ValidationError


class wizard_renling(models.TransientModel):
    _name = 'wizard.create.other'



    tb_po_id = fields.Many2one('tb.po.invoice')
    is_yjzy_tb_po_invoice = fields.Boolean('是否有对应下级账单')
    yjzy_type_1 = fields.Selection(
        [('sale', u'应付'), ('purchase', u'采购'), ('back_tax', u'退税'), ('other_payment_sale', '其他应收'),
         ('other_payment_purchase', '其他应付')], string=u'发票类型')  # 825

    def apply(self):
        self.tb_po_id.create_tb_po_invoice()

    def cancel_create(self):
        self.tb_po_id.action_submit()



#####################################################################################################################
