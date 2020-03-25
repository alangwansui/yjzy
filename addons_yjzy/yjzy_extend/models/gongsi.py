# -*- coding: utf-8 -*-

from odoo import models, fields, api


class gongsi(models.Model):
    _name = 'gongsi'
    _description = '内部公司'



    name = fields.Char('公司')
    partner_id = fields.Many2one('res.partner', '合作伙伴')
