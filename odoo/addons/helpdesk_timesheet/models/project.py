# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectTaskType(models.Model):
    _inherit = 'project.task.type'

    is_closed = fields.Boolean('Is a close stage', help="Tasks in this stage are considered as closed.")


class Project(models.Model):
    _inherit = 'project.project'

    ticket_ids = fields.One2many('helpdesk.ticket', 'project_id', string='Tickets')
    ticket_count = fields.Integer('# Tickets', compute='_compute_ticket_count')

    @api.depends('ticket_ids.project_id')
    def _compute_ticket_count(self):
        result = self.env['helpdesk.ticket'].read_group([
            ('project_id', 'in', self.ids)
        ], ['project_id'], ['project_id'])
        data = {data['project_id'][0]: data['project_id_count'] for data in result}
        for project in self:
            project.ticket_count = data.get(project.id, 0)
