# -*- coding: utf-8 -*-

from odoo import models, api, fields


class GlobalSearchConfigTemplate(models.Model):
    _name = 'global.search.config.template'
    _rec_name = 'model_id'

    @api.multi
    def _search_model(self):
        models = self.env['ir.model'].search([('state', '!=', 'manual'), ('transient', '=', False)])
        model_ids = [model.id for model in models if
                     self.env['ir.model.access'].sudo(user=self.env.user.id).check(model.model, 'read',
                                                                                   raise_exception=False)]
        return [('id', 'in', model_ids)]

    model_id = fields.Many2one('ir.model', 'Model', domain=_search_model, required=True)
    field_ids = fields.Many2many('ir.model.fields', string='Fields',
                                 domain="[('model_id', '=', model_id), ('name', '!=', 'id'), ('ttype', '!=', 'boolean'), ('selectable', '=', True)]",
                                 required="1")

    _sql_constraints = [
        ('uniq_model', "UNIQUE(model_id)", "The Model must be unique."),
    ]

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.field_ids = [(6, 0, [])]


class GlobalSearchConfig(models.Model):
    _name = 'global.search.config'
    _rec_name = 'model_id'

    template_id = fields.Many2one('global.search.config.template', 'Template', domian="[('id', in, [])]")
    user_id = fields.Many2one('res.users', 'User', default=lambda self: self.env.user, copy=False)
    customized = fields.Boolean('Customized')
    model_id = fields.Many2one('ir.model', 'Model', required=True, )
    field_ids = fields.Many2many('ir.model.fields', string='Fields',
                                 domain="[('model_id', '=', model_id), ('name', '!=', 'id'), ('ttype', '!=', 'boolean'), ('selectable', '=', True)]",
                                 required="1", order="ir_model_fields_id.field_description desc")

    _sql_constraints = [
        ('uniq_template_user', "UNIQUE(template_id, user_id)", "The template must be unique per user."),
    ]

    @api.multi
    def write(self, vals):
        if 'customized' not in vals and ((vals.get('user_id') and len(vals.keys()) > 1) or not vals.get('user_id')):
            vals['customized'] = True
        if 'template_id' in vals and not vals.get('model_id', False):
            vals['model_id'] = self.env['global.search.config.template'].search(
                [('id', '=', vals.get('template_id'))]).model_id.id
        return super(GlobalSearchConfig, self).write(vals)

    @api.model
    def create(self, vals):
        if 'template_id' in vals and not vals.get('model_id', False):
            vals['model_id'] = self.env['global.search.config.template'].search(
                [('id', '=', vals.get('template_id'))]).model_id.id
        return super(GlobalSearchConfig, self).create(vals)

    @api.onchange('user_id')
    def _onchange_user_id(self):
        dom = {'template_id': [('id', 'in', [])]}
        if self.user_id:
            models = self.env['ir.model'].search([('state', '!=', 'manual'), ('transient', '=', False)])
            model_ids = [model.id for model in models if
                         self.env['ir.model.access'].sudo(user=self.user_id.id).check(model.model, 'read',
                                                                                      raise_exception=False)]
            dom['template_id'] = [('model_id', 'in', model_ids)]
            dom['model_id'] = [('id', 'in', model_ids)]
        return {'domain': dom}

    @api.onchange('template_id')
    def _onchange_template_id(self):
        for rec in self:
            rec.set_values_template(rec.template_id)

    @api.onchange('model_id')
    def _onchange_model_id(self):
        if self.template_id:
            self._onchange_template_id()
        else:
            self.field_ids = [(6, 0, [])]

    @api.multi
    def set_values_template(self, template_id):
        for rec in self:
            rec.field_ids = [(6, 0, template_id.field_ids.ids)]
            rec.model_id = template_id.model_id.id
            rec.customized = False

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
