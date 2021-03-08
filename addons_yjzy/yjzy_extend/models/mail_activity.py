# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
import pytz

from odoo import api, exceptions, fields, models, _

class MailActivityType(models.Model):
    """ Activity Types are used to categorize activities. Each type is a different
    kind of activity e.g. call, mail, meeting. An activity can be generic i.e.
    available for all models using activities; or specific to a model in which
    case res_model_id field should be used. """
    _inherit = 'mail.activity.type'
    category = fields.Selection(selection_add=[('plan_check', '计划检查')])



class MailActivity(models.Model):
    """ An actual activity to perform. Activities are linked to
    documents using res_id and res_model_id fields. Activities have a deadline
    that can be used in kanban view to display a status. Once done activities
    are unlinked and a message is posted. This message has a new activity_type_id
    field that indicates the activity linked to the message. """
    _inherit = 'mail.activity'

    date_finish = fields.Date('完成时间')
    plan_check_id = fields.Many2one('plan.check','检查点',ondelete='cascade',)
    date_deadline = fields.Date('Due Date', index=True, required=False, )
    plan_check_line_id = fields.Many2one('plan.check.line','检查点',ondelete='cascade',)





