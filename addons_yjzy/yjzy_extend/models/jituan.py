# -*- coding: utf-8 -*-

from odoo import api, fields, models



class jituan(models.Model):
    _name = 'ji.tuan'
    _description = '集团'

    name = fields.Char('名称')
    description = fields.Text('描述')
    user_id = fields.Many2one('res.users', '用户')
    assistant_id = fields.Many2one('res.users', '助理')
    partner_ids = fields.One2many('res.partner', 'jituan_id', '客户')
    customer = fields.Boolean('客户')
    supplier = fields.Boolean('供应商')
    partner_type = fields.Selection([('customer',u'客户'),('supplier',u'供应商')])

