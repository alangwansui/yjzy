# -*- coding: utf-8 -*-
from password_generator import PasswordGenerator
from odoo import fields, models, api, _
from odoo.exceptions import Warning, UserError


class wizard_batch_passwd(models.TransientModel):
    _inherit = 'change.password.wizard'
    _description = '批量密码修改'

    def _default_user_ids(self):
        print('===ctx=1', self.env.context)
        user_ids = self._context.get('active_model') == 'res.users' and self._context.get('active_ids') or []
        pwo = PasswordGenerator()
        pwo.minlen = 8
        pwo.maxlen = 8
        pwo.minuchars = 1
        pwo.minlchars = 1
        pwo.minnumbers = 5
        pwo.minschars = 1
        auto_new_pwd = self.env.context.get('auto_new_pwd')

        def get_pwd(auto_new_pwd, pwo):
            res = auto_new_pwd and pwo.generate() or ''
            return res

        return [
            (0, 0, {'user_id': user.id, 'user_login': user.login, 'new_passwd': get_pwd(auto_new_pwd, pwo)})
            for user in self.env['res.users'].browse(user_ids)
        ]

    minlen = fields.Integer('最小长度', default=8)
    maxlen = fields.Integer('最大长度', default=8)
    minuchars = fields.Integer('最少大写字符', default=1)
    minlchars = fields.Integer('最少小写字符', default=1)
    minnumbers = fields.Integer('最少数字', default=5)
    minschars = fields.Integer('最少特殊符号', default=1)
    user_ids = fields.One2many('change.password.user', 'wizard_id', string='Users', default=_default_user_ids)




class ChangePasswordUser(models.TransientModel):
    _inherit = 'change.password.user'

    @api.multi
    def change_password_button(self):

        print('=================', self.env.context)
        if self.env.context.get('auto_new_pwd'):
            for line in self:
                line.user_id.write({'new_pwd': line.new_passwd})

        res = super(ChangePasswordUser, self).change_password_button()

        return res








