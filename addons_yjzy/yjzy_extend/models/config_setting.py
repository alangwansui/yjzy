# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_commission = fields.Float(string=u"经营费用计提比例", digits=(2, 4))

    # @api.model
    # def get_values(self):
    #     res = super(ResConfigSettings, self).get_values()
    #     ICPSudo = self.env['ir.config_parameter'].sudo()
    #     sale_commissions_str = ICPSudo.get_param('addons_yjzy.sale_commission',  '0.015')
    #     sale_commission = float(sale_commissions_str)
    #     res.update({'sale_commission': sale_commission})
    #     return res
    #
    # @api.multi
    # def set_values(self):
    #     super(ResConfigSettings, self).set_values()
    #     ICPSudo = self.env['ir.config_parameter'].sudo()
    #     ICPSudo.set_param('addons_yjzy.sale_commission',  '%s' % self.sale_commission)
