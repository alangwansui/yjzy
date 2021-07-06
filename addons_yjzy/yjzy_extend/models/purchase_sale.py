# -*- coding: utf-8 -*-
import math

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning
from odoo.osv import expression
from odoo.addons.purchase.models.purchase import PurchaseOrder



class purchase_order(models.Model):
    _inherit = 'purchase.order'
    #13已经添加

    @api.depends('order_line', 'order_line.sol_id_price_total')
    def compute_qty_received_amount(self):
        for one in self:
            qty_received_amount = sum(x.qty_received for x in one.order_line)
            one.qty_received_amount = qty_received_amount
    qty_received_amount = fields.Float('发货数量',compute='compute_qty_received_amount',store=True)
    so_approve_date = fields.Date('合规审批时间',related='source_so_id.approve_date',store=True)





class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'



###############################
