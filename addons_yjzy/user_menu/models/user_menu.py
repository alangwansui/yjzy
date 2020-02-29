# -*- coding: utf-8 -*-
import pytz
from datetime import datetime, timedelta, date
from odoo.exceptions import Warning
from odoo.tools.safe_eval import safe_eval
from odoo import models, fields, api
from jinja2 import Template
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
import logging




_logger = logging.getLogger(__name__)


def Date_Time_Compute(day_str='now', days=0, hours=0, flag=1, fmt=DTF, tz='UTC'):
    """
    tz = 'Asia/Shanghai'  'UTC'
    """

    t = datetime.now(pytz.timezone(tz))
    if day_str == 'now':
        pass
    if day_str == 'start':
        t = datetime.strptime(t.strftime(DF + ' 00:00:00'), DTF)
    if day_str == 'end':
        t = datetime.strptime(t.strftime(DF + ' 23:59:59'), DTF)

    return (t + timedelta(days=days, hours=hours)).strftime(DTF)









class IrActionsActWindowView(models.Model):
    _inherit = 'ir.actions.act_window.view'
    user_menu_id = fields.Many2one('user.menu', 'UserMenu')


class user_menu(models.Model):
    _name = 'user.menu'
    _inherit = 'ir.actions.act_window'
    _order = 'sequence'
    _description = '工作看板'

    name = fields.Char(u'名称', required=True)
    user_id = fields.Many2one('res.users', u'用户')
    user_ids = fields.Many2many('res.users', 'ref_menu_user_menu', 'mid', 'umid',  u'用户')
    len_records = fields.Integer(u'数量', compute='compute_len_records')

    dynamic_template = fields.Text('模板a')
    dynamic_code = fields.Text('动态数据代码a')
    dynamic_html = fields.Text('动态内容a', compute='compute_dynamic_html')

    dynamic_template_b = fields.Text('模板b')
    dynamic_code_b = fields.Text('动态数据代码b')
    dynamic_html_b = fields.Text('动态内容b', compute='compute_dynamic_html')

    dynamic_template_c = fields.Text('模板c')
    dynamic_code_c = fields.Text('动态数据代码d')
    dynamic_html_c = fields.Text('动态内容d', compute='compute_dynamic_html')

    view_ids = fields.One2many('ir.actions.act_window.view', 'user_menu_id', string='Views')

    sequence = fields.Integer('排序')
    color = fields.Integer('颜色')

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
                    globals_dict = {
                        'self': one, 'uid': one._uid, 'datetime': datetime, 'len': len,
                        'today': fields.date.today().strftime(DF), 'fields': fields,
                        'context_today': fields.date.today,
                        'relativedelta': timedelta,
                        'dt': Date_Time_Compute,
                    }

                    dic_a = safe_eval(one.dynamic_code, globals_dict)
                    html_a = Template(one.dynamic_template).render(**dic_a)
                    one.dynamic_html = html_a

                    dic_b = safe_eval(one.dynamic_code_b, globals_dict)
                    html_b = Template(one.dynamic_template_b).render(**dic_b)
                    one.dynamic_html_b = html_b

                    dic_c = safe_eval(one.dynamic_code_c, globals_dict)
                    html_c = Template(one.dynamic_template_c).render(**dic_c)
                    one.dynamic_html_c = html_c

                except Exception as e:
                    _logger.warn(e)
                    #raise Warning(e)


    def do_acton(self):
        ctx = self.env.context
        act_id, act_dm, act_uid, act_ctx = ctx.get('act_id'), ctx.get('act_dm'), ctx.get('act_uid'), ctx.get('act_ctx')

        if not act_id:
            raise Warning('必须提供动作ID')

        action = self.env.ref(act_id).read()[0]
        globals_dict = {'uid': self._uid}
        if act_dm:
            action['domain'] = str(act_dm + safe_eval(action['domain'], globals_dict))

        if act_ctx:
            context = safe_eval(action['context'], globals_dict)
            context.update(act_ctx)
            action['context'] = str(context)

        return action










