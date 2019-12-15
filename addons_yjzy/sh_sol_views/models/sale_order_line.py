# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields,models,api

class QuotationOrderLine(models.Model):
    _inherit = 'sale.order.line'

    so_order_date = fields.Datetime(related="order_id.date_order",string="Date Order")