# -*- coding: utf-8 -*-


from odoo import api, fields, models, _

class ir_model(models.Model):
    _inherit = 'ir.model'

    force_auto_subscribe = fields.Boolean(u'不取消自动关注')

    @api.model
    def get_force_auto_subscribe(self, model):
        one = self.search([('model','=',model)], limit=1)
        return one.force_auto_subscribe