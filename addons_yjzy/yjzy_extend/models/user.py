# -*- coding: utf-8 -*-

from odoo import models, fields, api


class res_users(models.Model):
    _inherit = 'res.users'

    salesman_code = fields.Char(u'销售员编码')
    assistant_id = fields.Many2one('res.users', u'业务员')
    product_manager_id = fields.Many2one('res.users', u'产品经理')
    leader_user_id = fields.Many2one('res.users', u'直接上级用户', compute='get_leader_user')
    sign_image = fields.Binary(u'签名', widget='image')
    new_pwd = fields.Char('new_pwd')

    def get_leader_user(self):
        for one in self:
            one.leader_user_id = one.employee_id.parent_id.user_id

    # @api.multi #参考
    # def write(self,vals):
    #     res = super(res_users, self).write(vals)
    #     if 'company_id' in vals:
    #         self.partner_id.compute_supplier_amount_invoice_advance_payment()
    #         print('test',self.partner_id)
    #     return res


