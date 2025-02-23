
from odoo.osv import expression
import re
from odoo import models, fields, api, _, tools, SUPERUSER_ID, registry
from odoo.exceptions import Warning
import logging

_logger = logging.getLogger(__name__)


class personal_tag(models.Model):
    _name = 'personal.tag'
    _description = u'通讯录分组'

    name = fields.Char(u'名称', required=True)
    code = fields.Char(u'编码')
    is_default = fields.Boolean('默认分组',)


class personal_partner(models.Model):
    _name = 'personal.partner'
    _rec_name = 'display_name'

    _description = '通讯录'

    @api.depends('name', 'email')
    def _compute_display(self):
        for one in self:
            if one.name:
                one.display_name = '<%s> %s' % (one.email, one.name)
            else:
                one.display_name = '<%s>' % one.email


    @api.model
    def get_default_tag(self):
        ctx = self.env.context
        tag_code = ctx.get('tag_code', 'normal')
        tag = self.env['personal.tag'].search([('code','=',tag_code)])
        return tag.id

    display_name = fields.Char(compute=_compute_display, store=True, string=u'邮箱', readonly=False)
    name = fields.Char(u'名称', required=False)
    email = fields.Char(u'电子邮件', required=True)
    address = fields.Char(u'地址')
    function = fields.Char(u'工作岗位')
    phone = fields.Char(u'电话')
    mobile = fields.Char(u'手机')
    qq = fields.Char('QQ')
    partner_id = fields.Many2one('res.partner', u'内部联系人')
    tag_id = fields.Many2one('personal.tag', u'通讯录分组', default=get_default_tag)
    user_id = fields.Many2one('res.users', u'用户', default=lambda self: self._uid)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):

        print ('=====', name, args, operator)

        if operator in ('ilike', 'like', '=', '=like', '=ilike'):
            args = expression.AND([args or [], ['|', ('name', operator, name), ('email', operator, name)]])

            print('=====', name, args, operator)



        return super(personal_partner, self).name_search(name=name, args=args, operator=operator, limit=limit)


    @api.constrains('email')
    def check_email(self):
        for one in self:
            if not ('@' in one.email):
                raise Warning('%s 不是合格的电子邮件格式,一个正确的邮箱格式比如这样 demo@qq.com' % one.email)
            # if not re.match(r'^[\.0-9a-zA-Z_]{0,19}@[0-9a-zA-A-Z]{1,13}\.[a-zA-Z]{1,4}.*$', one.email):
            #     raise Warning('%s 不是合格的电子邮件格式,一个正确的邮箱格式比如这样 demo@qq.com' % one.email)


    def write(self, values):
        if 'email' in values:
            values.update({
                'email': values['email'].lower()
            })
        return super(personal_partner, self).write(values)



    @api.model
    def name_create(self, name):
        vals = {
            'email': name.lower(),
        }
        return self.create(vals).name_get()[0]


    @api.constrains('user_id', 'email')
    def check_uniq(self):
        for one in self:
            if self.search_count([('user_id', '=', one.user_id.id), ('email', '=', one.email)]) > 1:
                raise Warning('用户和邮箱不能重复')


