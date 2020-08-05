# -*- coding: utf-8 -*-

from odoo import models, fields, api


class dynamic_view(models.Model):
    _name = 'dynamic.view'

    name = fields.Char(u'Name')
    active = fields.Boolean(u'Active', default=True)
    type = fields.Selection([('tree', 'Tree'), ('form', 'Form'), ('search', 'Search')], 'Type', default='tree',
                            required=True)
    user_id = fields.Many2one('res.users', u'User')
    model_id = fields.Many2one('ir.model', u'Model', required=True)
    line_ids = fields.One2many('dynamic.view.line', 'dynamic_view_id', 'Lines')
    line_ids2 = fields.One2many('dynamic.view.line', 'dynamic_view_id2', 'Lines')
    line_ids3 = fields.One2many('dynamic.view.line', 'dynamic_view_id3', u'Lines')
    is_global = fields.Boolean('Global')
    button_ids = fields.One2many('dynamic.view.button', 'dynamic_view_id', u'Button')

    @api.onchange('user_id')
    def onchange_user(self):
        self.is_global = not bool(self.user_id)


class dynamic_view_line(models.Model):
    _name = 'dynamic.view.line'

    dynamic_view_id = fields.Many2one('dynamic.view', 'Dynamic View', required=False)
    dynamic_view_id2 = fields.Many2one('dynamic.view', 'Dynamic View', required=False)
    dynamic_view_id3 = fields.Many2one('dynamic.view', 'Dynamic View', required=False)

    field_id = fields.Many2one('ir.model.fields', 'Field', required=True)
    invisible = fields.Boolean('Invisible', default=False)
    required = fields.Boolean('Required', default=False)
    readonly = fields.Boolean('Readonly', default=False)
    no_create = fields.Boolean('No Create', default=False)
    no_open = fields.Boolean('No Open', default=False)
    group_ids = fields.Many2many('res.groups', 'ref_vb_group', 'gid', 'bid', u'Groups')

    position = fields.Selection([('last', u'Last'), ('first', u'First'), ('before', u'Before'), ('after', u'After'), ],
                                u'Position', default='last')
    position_field = fields.Many2one('ir.model.fields', u'Position Field', required=False)


class dynamic_view_button(models.Model):
    _name = "dynamic.view.button"

    dynamic_view_id = fields.Many2one('dynamic.view', 'Dynamic View', required=False)
    name = fields.Char(u'Button Name')
    string = fields.Char(u'New Lable')
    invisible = fields.Boolean(u'Invisible', default=False)

    highlight = fields.Boolean('High Light', default=True)

    hlight = fields.Selection([('nochange', u'No Change'), ('yes', u'Set High Light'), ('no', u'Cancel High Light')],
                              u'High Light', default='nochange')

    confirm_text = fields.Text(u'Pop Confirm')
    group_ids = fields.Many2many('res.groups', 'ref_vb_group', 'gid', 'bid', u'Groups')
    user_ids = fields.Many2many('res.users', 'ref_vb_user', 'fid', 'tid', 'Users')
    @api.depends('group_ids')
    def _compute_group_str(self):
        data_obj = self.env['ir.model.data']
        xml_ids = []
        for g in self.group_ids:
            data = data_obj.search([('res_id', '=', g.id), ('model', '=', 'res.groups')])
            xml_ids.append(data.complete_name)
        self.group_str = xml_ids and ','.join(xml_ids) or ''
