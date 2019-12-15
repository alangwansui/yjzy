# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import Warning


class ir_model(models.Model):
    _inherit = 'ir.model'

    need_comb_trans = fields.Boolean(u'需要同时显示双语')

    def write(self, vals):
        res = super(ir_model, self).write(vals)
        if 'need_comb_trans' in vals:
            self.env['ir.translation'].with_context(force_recompute=1)._get_need_comb_models()
        return res


class ir_translation(models.Model):
    _inherit = 'ir.translation'

    _Need_Comb_Models = []

    @api.model
    def _get_need_comb_models(self):
        if (not self._Need_Comb_Models) or self.env.context.get('force_recompute'):
            self._Need_Comb_Models = [x.model for x in self.env['ir.model'].search([('need_comb_trans', '=', True)])]
        return self._Need_Comb_Models

    @api.depends('src', 'value')
    def _compute_comb_value(self):

        model_names = self._get_need_comb_models()

        for one in self:
            if one.type == 'model' and one.name.split(',')[0] in model_names:
                src = one.src or ''
                value = one.value or ''
                one.comb_value = '%s:%s' % (src, value)
            else:
                one.comb_value = one.value

    comb_value = fields.Char(u'原文和翻译', compute=_compute_comb_value, store=True)

    def rush_comb_value(self):
        self.search([])._compute_comb_value()
