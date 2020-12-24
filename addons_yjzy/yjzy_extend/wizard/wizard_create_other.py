# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp
from lxml import etree
from odoo.exceptions import UserError, ValidationError


class wizard_renling(models.TransientModel):
    _name = 'wizard.create.other'



    tb_po_id = fields.Many2one('tb.po.invoice')

    def apply(self):
        self.tb_po_id.create_tb_po_invoice()



#####################################################################################################################
