# -*- coding: utf-8 -*-
from odoo.tools.safe_eval import safe_eval
from odoo import models, fields, api
from jinja2 import Template





class user_menu(models.Model):
    _name = 'user.menu'
    _inherit = 'ir.actions.act_window'
    _description = '工作看板'

    name = fields.Char(u'名称', required=True)
    user_id = fields.Many2one('res.users', u'用户')
    user_ids = fields.Many2many('res.users', 'ref_menu_user_menu', 'mid', 'umid',  u'用户')
    len_records = fields.Integer(u'数量', compute='compute_len_records')

    dynamic_template = fields.Text('模板', default='Hello {{ name }}')
    dynamic_code = fields.Text('动态数据代码', default="{'name': self.name}")
    dynamic_html = fields.Text('动态内容', compute='compute_dynamic_html')


    def compute_len_records(self):
        gb_var = {'uid': self._uid}
        for one in self:
            domain = safe_eval(one.domain or '[]', gb_var)
            one.len_records = one.env[one.res_model].search_count(domain)

    def open_action(self):
        action = self.read()[0]
        return action

    def compute_dynamic_html(self):
        for one in self:
            if one.dynamic_template and one.dynamic_code:
                template = Template(one.dynamic_template)
                globals_dict = {'self': one, 'uid': one._uid}
                ctx = safe_eval(one.dynamic_code, globals_dict)
                html = template.render(**ctx)
                one.dynamic_html = html



