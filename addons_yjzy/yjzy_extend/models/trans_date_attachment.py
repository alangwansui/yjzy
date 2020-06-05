# -*- coding: utf-8 -*-

from odoo import api, fields, models



class trans_date_attachment(models.Model):
    _name = 'trans.date.attachment'
    _description = '附件管理'

    name = fields.Char('编号', default=lambda self: self.env['ir.sequence'].next_by_code('trans.date.attachment'))
    attachment = fields.Many2many('ir.attachment', string='进仓日附件')
    type = fields.Selection([('date_out_in', u'1'),
                               ('date_ship', u'2'),
                               ('date_customer_finish', u'3'),
                               ],
                              string=u'type', track_visibility='onchange')
    tb_id = fields.Many2one('transport.bill',u'出运合同')


