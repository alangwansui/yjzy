from odoo import models, fields, api, _, tools, SUPERUSER_ID, registry
from odoo.exceptions import Warning
import logging

_logger = logging.getLogger(__name__)


class personal_tag(models.Model):
    _name = 'personal.tag'
    _description = u'通讯录分组'

    name = fields.Char(u'名称', required=True)


class personal_partner(models.Model):
    _name = 'personal.partner'
    _rec_name = 'email'

    _description = '通讯录'

    def _compute_display_name(self):
        for one in self:
            one.display_name = '%s <%s>' % (one.name, one.email)

    display_name = fields.Char(compute='_compute_display_name', store=True, string=u'邮箱')
    name = fields.Char(u'名称', required=False)
    email = fields.Char(u'电子邮件', required=True)
    address = fields.Char(u'地址')
    function = fields.Char(u'工作岗位')
    phone = fields.Char(u'电话')
    mobile = fields.Char(u'手机')
    partner_id = fields.Many2one('res.partner', u'内部联系人')
    tag_id = fields.Many2one('personal.tag', u'通讯录分组')
    user_id = fields.Many2one('res.users', u'用户', default=lambda self: self._uid)

    @api.model
    def name_create(self, name):
        print('==========name_create======', name)

        vals = {
            'email': name,

        }
        s = self.create(vals).name_get()[0]
        print('==========name_create2======', s)
        return s





    @api.constrains('user_id', 'email')
    def check_uniq(self):
        for one in self:
            if self.search_count([('user_id', '=', one.user_id.id), ('email', '=', one.email)]) > 1:
                raise Warning('用户和邮箱不能重复')


