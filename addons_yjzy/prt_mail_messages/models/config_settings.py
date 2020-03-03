# -*- coding: utf-8 -*-

from odoo import fields, models, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    baidu_app_key = fields.Char(u'百度API-KEY')

    @api.model
    def get_values(self):
        print('==get_values==')
        res = super(ResConfigSettings, self).get_values()
        res.update(
            baidu_app_key=self.env['ir.config_parameter'].sudo().get_param('baidu_app_key')
        )
        print('==get_values==', res)
        return res

    @api.multi
    def set_values(self):
        print('==set_values==', self.baidu_app_key)
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('baidu_app_key', self.baidu_app_key)


