# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval



class Task(models.Model):
    _inherit = "project.task"

    daniel_comments = fields.Text('海峰备注', track_visibility='onchange')
    benz_comments = fields.Text('正益备注', track_visibility='onchange')

    def open_wizard_comments(self):
        comments_obj = self.env['wizard.project.task.comments']
        user = self.env.user.login
        if user == 'daniel':
            comments = comments_obj.create({
                'project_task_id': self.id,
                'type':'daniel',
            })
        else:
            comments = comments_obj.create({
                'project_task_id': self.id,
                'type': 'benz',
            })
        form_view = self.env.ref('yjzy_extend.wizard_project_task_comments_form')
        return {
            'name': u'查看',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.project.task.comments',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': comments.id,
            'target': 'new',
            'context': {}
        }