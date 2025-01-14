# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.fields import Datetime


class MarketingParticipant(models.Model):
    _name = 'marketing.participant'
    _description = 'Marketing Participant'
    _rec_name = 'resource_ref'

    @api.model
    def default_get(self, default_fields):
        defaults = super(MarketingParticipant, self).default_get(default_fields)
        if not defaults.get('res_id'):
            model_name = defaults.get('model_name')
            if not model_name and defaults.get('campaign_id'):
                model_name = self.env['marketing.campaign'].browse(defaults['campaign_id']).model_name
            if model_name:
                resource = self.env[model_name].search([], limit=1)
                defaults['res_id'] = resource.id
        return defaults

    @api.model
    def _selection_target_model(self):
        models = self.env['ir.model'].search([('is_mail_thread', '=', True)])
        return [(model.model, model.name) for model in models]

    campaign_id = fields.Many2one('marketing.campaign', string='Campaign', ondelete='cascade', required=True)
    model_id = fields.Many2one(
        'ir.model', string='Object', related='campaign_id.model_id',
        index=True, readonly=True, store=True)
    model_name = fields.Char(
        string='Record model', related='campaign_id.model_id.model',
        readonly=True, store=True)
    res_id = fields.Integer(string='Record ID', index=True)
    resource_ref = fields.Reference(
        string='Record', selection='_selection_target_model',
        compute='_compute_resource_ref', inverse='_set_resource_ref')
    trace_ids = fields.One2many('marketing.trace', 'participant_id', string='Actions')
    state = fields.Selection([
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('unlinked', 'Removed'),
        ], default='running', index=True, required=True,
        help='Removed means the related record does not exist anymore.')

    @api.depends('model_name', 'res_id')
    def _compute_resource_ref(self):
        for participant in self:
            if participant.model_name:
                participant.resource_ref = '%s,%s' % (participant.model_name, participant.res_id or 0)

    def _set_resource_ref(self):
        for participant in self:
            if participant.resource_ref:
                participant.res_id = participant.resource_ref.id

    def check_completed(self):
        existing_traces = self.env['marketing.trace'].search([
            ('participant_id', 'in', self.ids),
            ('state', '=', 'scheduled'),
        ])
        (self - existing_traces.mapped('participant_id')).write({'state': 'completed'})

    @api.model
    def create(self, values):
        res = super(MarketingParticipant, self).create(values)
        # prepare first traces related to begin activities
        primary_activities = res.campaign_id.marketing_activity_ids.filtered(lambda act: act.trigger_type == 'begin')
        now = Datetime.from_string(Datetime.now())
        trace_ids = [
            (0, 0, {
                'activity_id': activity.id,
                'schedule_date': now + relativedelta(**{activity.interval_type: activity.interval_number}),
            }) for activity in primary_activities]
        res.write({'trace_ids': trace_ids})
        return res

    def action_set_completed(self):
        ''' Manually mark as a completed and cancel every scheduled trace '''
        # TDE TODO: delegate set Canceled to trace record
        self.write({'state': 'completed'})
        self.env['marketing.trace'].search([
            ('participant_id', 'in', self.ids),
            ('state', '=', 'scheduled')
        ]).write({
            'state': 'canceled',
            'schedule_date': Datetime.now(),
            'state_msg': _('Marked as completed')
        })

    def action_set_running(self):
        self.write({'state': 'running'})

    def action_set_unlink(self):
        self.write({'state': 'unlinked'})
        self.env['marketing.trace'].search([
            ('participant_id', 'in', self.ids),
            ('state', '=', 'scheduled')
        ]).write({
            'state': 'canceled',
            'state_msg': _('Record deleted'),
        })
        return True


class MarketingTrace(models.Model):
    _name = 'marketing.trace'
    _description = 'Marketing Trace'
    _order = 'schedule_date DESC'
    _rec_name = 'participant_id'

    participant_id = fields.Many2one(
        'marketing.participant', string='Participant',
        index=True, ondelete='cascade', required=True)
    res_id = fields.Integer(string='Document ID', related='participant_id.res_id', index=True, store=True)
    activity_id = fields.Many2one(
        'marketing.activity', string='Activity',
        index=True, ondelete='cascade', required=True)
    activity_type = fields.Selection(related='activity_id.activity_type', readonly=True)
    trigger_type = fields.Selection(related='activity_id.trigger_type', readonly=True)

    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('processed', 'Processed'),
        ('rejected', 'Rejected'),
        ('canceled', 'Canceled'),
        ('error', 'Error')
        ], default='scheduled', index=True, required=True)
    schedule_date = fields.Datetime()
    state_msg = fields.Char(string='Error message')
    # hierarchy
    parent_id = fields.Many2one('marketing.trace', string='Parent', index=True, ondelete='cascade')
    child_ids = fields.One2many('marketing.trace', 'parent_id', string='Direct child traces')
    # statistics
    mail_statistics_ids = fields.One2many('mail.mail.statistics', 'marketing_trace_id', string='Mass mailing statistics')
    sent = fields.Datetime(related='mail_statistics_ids.sent')
    exception = fields.Datetime(related='mail_statistics_ids.exception')
    opened = fields.Datetime(related='mail_statistics_ids.opened')
    replied = fields.Datetime(related='mail_statistics_ids.replied')
    bounced = fields.Datetime(related='mail_statistics_ids.bounced')
    clicked = fields.Datetime(related='mail_statistics_ids.clicked')

    def participant_action_cancel(self):
        self.action_cancel(message=_('Manually'))

    def action_cancel(self, message=None):
        values = {'state': 'canceled', 'schedule_date': Datetime.now()}
        if message:
            values['state_msg'] = message
        self.write(values)
        self.mapped('participant_id').check_completed()

    def action_execute(self):
        self.activity_id.execute_on_traces(self)

    def process_event(self, action):
        """Process event coming from customers currently centered on email actions.
        It updates child traces :

         * opposite actions are canceled, for example mail_not_open when mail_open is triggered;
         * bounced mail cancel all child actions not being mail_bounced;

        :param string action: see trigger_type field of activity
        """
        self.ensure_one()
        if self.participant_id.campaign_id.state not in ['draft', 'running']:
            return

        now = Datetime.from_string(Datetime.now())
        msg = {
            'mail_not_reply': _('Parent activity mail replied'),
            'mail_not_click': _('Parent activity mail clicked'),
            'mail_not_open': _('Parent activity mail opened'),
            'mail_bounce': _('Parent activity mail bounced'),
        }

        opened_child = self.child_ids.filtered(lambda trace: trace.state == 'scheduled')

        if action in ['mail_reply', 'mail_click', 'mail_open']:
            for next_trace in opened_child.filtered(lambda trace: trace.activity_id.trigger_type == action):
                if next_trace.activity_id.interval_number == 0:
                    next_trace.write({
                        'schedule_date': now,
                    })
                    next_trace.activity_id.execute_on_traces(next_trace)
                else:
                    next_trace.write({
                        'schedule_date': now + relativedelta(**{
                            next_trace.activity_id.interval_type: next_trace.activity_id.interval_number
                        }),
                    })

            opposite_trigger = action.replace('_', '_not_')
            opened_child.filtered(
                lambda trace: trace.activity_id.trigger_type == opposite_trigger
            ).action_cancel(message=msg[opposite_trigger])

        elif action == 'mail_bounce':
            opened_child.filtered(
                lambda trace: trace.activity_id.trigger_type != 'mail_bounce'
            ).action_cancel(message=msg[action])

        return True
