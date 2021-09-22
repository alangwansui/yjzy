# -*- coding: utf-8 -*-

from odoo import models, fields, api


class wizard_project_task_comments(models.TransientModel):
    _name = 'wizard.project.task.comments'

    comments = fields.Text('备注日志', )
    project_task_id = fields.Many2one('project.task')
    type = fields.Selection([('daniel', 'Daniel'), ('benz', 'Benz')],
                            'type')

    def apply(self):
        type = self.type
        if type == 'daniel':
            self.project_task_id.write({
                'daniel_comments':self.comments,
            })
        else:
            self.project_task_id.write({
                'benz_comments':self.comments,
            })



