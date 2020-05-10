# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, tools
from odoo.tools import pycompat


class DashBoard(models.Model):
    _name = 'dashboard.dashboard'
    #_inherit = ['board.board']
    _description = "自定义仪表板"

    name = fields.Char('名称')
    user_id = fields.Many2one('res.users', '用户')
    view_ids = fields.One2many('dashboard.view', 'dashboard_id', '视图')


    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):

        if view_type == 'form':
            print('>>>>>>', view_type, self.env.context)

        res = super(DashBoard, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        dashboard_id = self.env.context.get('dashboard_id')
        if view_type == 'form' and dashboard_id:
            print('>>>>>>', view_type, dashboard_id)
            custom_view = self.env['dashboard.view'].search([('dashboard_id', '=', dashboard_id)], limit=1)
            if custom_view:
                res.update({'custom_view_id': custom_view.id,
                            'arch': custom_view.arch})
            res.update({
                'arch': self._arch_preprocessing(res['arch']),
                'toolbar': {'print': [], 'action': [], 'relate': []}
            })
        return res


    @api.model
    def _arch_preprocessing(self, arch):
        from lxml import etree
        def remove_unauthorized_children(node):
            for child in node.iterchildren():
                if child.tag == 'action' and child.get('invisible'):
                    node.remove(child)
                else:
                    remove_unauthorized_children(child)
            return node

        archnode = etree.fromstring(arch)
        return etree.tostring(remove_unauthorized_children(archnode), pretty_print=True, encoding='unicode')



class DashboardCustom(models.Model):
    _name = 'dashboard.view'
    _order = 'create_date desc'

    dashboard_id = fields.Many2one('dashboard.dashboard', '自定义面板')
    arch = fields.Text(string='View Architecture', required=True)







