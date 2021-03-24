# -*- coding: utf-8 -*-

from odoo import api, fields, models



class order_track_attachment(models.Model):
    _name = 'order.track.attachment'
    _description = '附件管理'


    attachment = fields.Many2many('ir.attachment', string='附件')
    plan_check_line_id = fields.Many2one('plan.check.line',u'检查点')
    plan_check_id = fields.Many2one('plan.check',u'检查点')
    comments = fields.Char('备注')


