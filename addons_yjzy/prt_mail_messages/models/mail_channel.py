# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _, SUPERUSER_ID
from odoo.exceptions import Warning

class mail_channel(models.Model):
    _inherit = 'mail.channel'

    sent_uid = fields.Many2one('res.users', u'发件所有者')
    chat_uid = fields.Many2one('res.users',  '系统通知用户')

    @api.multi
    def action_unfollow(self):
        raise Warning('不允许退出频道')
        #return self._action_unfollow(self.env.user.partner_id)





