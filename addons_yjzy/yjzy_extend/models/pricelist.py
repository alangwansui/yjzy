# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Pricelist(models.Model):
    _inherit = "product.pricelist"

    customer_id = fields.Many2one('res.partner', '客户')
