# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
import pytz
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import Warning, UserError
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
    order_track_id = fields.Many2one('order.track','活动计划',ondelete='cascade',)






    def action_feedback(self, feedback=False):
        strptime = datetime.strptime
        if strptime(self.date_finish, DF) > datetime.today():
            raise Warning('完成日期不能大于单日')
        if self.plan_check_line_id:
            self.plan_check_line_id.date_finish = self.date_finish#akiny
        if self.order_track_id:
            if self.activity_type_id.name == '计划填写进仓日':

                self.order_track_id.date_out_in = self.date_finish
                self.order_track_id.create_activity_plan_date_ship()
            elif self.activity_type_id.name == '计划填写船期':
                self.order_track_id.date_ship = self.date_finish
                self.order_track_id.create_activity_plan_date_customer_finish()
            elif self.activity_type_id.name == '计划填写客户交单日':
                self.order_track_id.date_customer_finish = self.date_finish


        message = self.env['mail.message']
        if feedback:
            self.write(dict(feedback=feedback))
        for activity in self:
            record = self.env[activity.res_model].browse(activity.res_id)
            record.message_post_with_view(
                'mail.message_activity_done',
                values={'activity': activity},
                subtype_id=self.env.ref('mail.mt_activities').id,
                mail_activity_type_id=activity.activity_type_id.id,
            )
            message |= record.message_ids[0]

        self.unlink()
        return message.ids and message.ids[0] or False

    @api.multi
    def action_close_dialog(self):
        if self.plan_check_line_id:
            self.plan_check_line_id.date_deadline = self.date_deadline
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_save_test(self):
        # your code
        self.ensure_one()
        # close popup
        return {'type': 'ir.actions.act_window_close'}