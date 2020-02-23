# -*- coding: utf-8 -*-
from odoo.tools.safe_eval import safe_eval
from odoo import models, fields



class user_menu(models.Model):
    _name = 'user.menu'
    _inherit = 'ir.actions.act_window'
    _description = '工作看板'

    name = fields.Char(u'名称', required=True)
    user_id = fields.Many2one('res.users', u'用户')
    len_records = fields.Integer('数量', compute='compute_len_records')

    def compute_len_records(self):
        gb_var = {'uid': self._uid}
        for one in self:
            domain = safe_eval(one.domain or '[]', gb_var)
            one.len_records = one.env[one.res_model].search_count(domain)

    def open_action(self):
        action = self.read()[0]
        return action



