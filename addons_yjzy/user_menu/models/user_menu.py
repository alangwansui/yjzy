# -*- coding: utf-8 -*-
from datetime import datetime
from odoo.exceptions import Warning
from odoo.tools.safe_eval import safe_eval
from odoo import models, fields, api
from jinja2 import Template
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
import logging

_logger = logging.getLogger(__name__)


class user_menu(models.Model):
    _name = 'user.menu'
    _inherit = 'ir.actions.act_window'
    _description = '工作看板'

    name = fields.Char(u'名称', required=True)
    user_id = fields.Many2one('res.users', u'用户')
    user_ids = fields.Many2many('res.users', 'ref_menu_user_menu', 'mid', 'umid',  u'用户')
    len_records = fields.Integer(u'数量', compute='compute_len_records')

    dynamic_template = fields.Text('模板')
    dynamic_code = fields.Text('动态数据代码')
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
                try:
                    template = Template(one.dynamic_template)
                    globals_dict = {'self': one, 'uid': one._uid, 'datetime': datetime, 'len': len, 'today': fields.date.today().strftime(DF), 'fields': fields}
                    dic_var = safe_eval(one.dynamic_code, globals_dict)
                    html = template.render(**dic_var)
                    one.dynamic_html = html
                except Exception as e:
                    pass
                    #raise Warning(e)


    def do_acton(self):
        ctx = self.env.context
        act_id, act_dm, act_uid = ctx.get('act_id'), ctx.get('act_dm'), ctx.get('act_uid')
        action = self.env.ref(act_id).read()[0]


        print( action['domain'], act_dm, type(action['domain']), type(act_dm))
        if act_dm:
            action['domain'] = str(act_dm + safe_eval(action['domain'], {'uid': self._uid}))

        print('====do_acton====', action)
        return action










