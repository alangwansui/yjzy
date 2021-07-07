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







class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'



###############################
