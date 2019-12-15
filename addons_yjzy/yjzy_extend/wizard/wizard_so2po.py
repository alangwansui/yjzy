# -*- coding: utf-8 -*-

from odoo import  fields, models, api, _
from odoo.exceptions import Warning

class wizard_so2po(models.TransientModel):
    _inherit = 'wizard.so2po'

    def make_purchase_orders(self):
        res = super(wizard_so2po, self).make_purchase_orders()

        return res
















