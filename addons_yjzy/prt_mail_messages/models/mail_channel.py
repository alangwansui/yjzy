# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _


class mail_channel(models.Model):
    _inherit = 'mail.channel'

    sent_uid = fields.Many2one('res.users', u'发件所有者')





