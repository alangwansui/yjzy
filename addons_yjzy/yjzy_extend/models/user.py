# -*- coding: utf-8 -*-

from odoo import models, fields


class res_users(models.Model):
    _inherit = 'res.users'

    salesman_code = fields.Char(u'销售员编码')
    assistant_id = fields.Many2one('res.users', u'业务员')
    product_manager_id = fields.Many2one('res.users', u'产品经理')

    leader_user_id = fields.Many2one('res.users', u'直接上级用户', compute='get_leader_user')

    sign_image = fields.Binary(u'签名', widget='image')

    def get_leader_user(self):
        for one in self:
            one.leader_user_id = one.employee_id.parent_id.user_id




