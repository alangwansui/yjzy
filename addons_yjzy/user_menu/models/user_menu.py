# -*- coding: utf-8 -*-
from odoo.tools.safe_eval import safe_eval
from odoo import models, fields


class user_menu(models.Model):
    _name = 'user.menu'
    _description = '用户看板菜单定义'

    name = fields.Char(u'名称', related='menu_id.name')
    user_id = fields.Many2one('res.users', u'用户')
    menu_id = fields.Many2one('ir.ui.menu', '菜单')

    len_records = fields.Integer('数量', compute='compute_len_records')

    def compute_len_records(self):
        for one in self:
            print(one.menu_id.action.domain)
            model = one.menu_id.action.res_model
            domian = safe_eval(one.menu_id.action.domain, {'uid': one._uid})


            one.len_records = len(one.env[model].search_read(domian, ['id']))

            print('===',  domian, one.len_records)





    def open_menu(self):
        action = self.menu_id.action.read()[0]
        return action



