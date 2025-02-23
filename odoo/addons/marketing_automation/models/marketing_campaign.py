# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

from datetime import timedelta, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.fields import Datetime
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class MarketingCampaign(models.Model):
    _name = 'marketing.campaign'
    _description = 'Marketing Campaign'
    _inherits = {'utm.campaign': 'utm_campaign_id'}
    _order = 'create_date DESC'

    utm_campaign_id = fields.Many2one('utm.campaign', 'UTM Campaign', ondelete='cascade', required=True)
    active = fields.Boolean(default=True)
    state = fields.Selection([
        ('draft', 'New'),
        ('running', 'Running'),
        ('stopped', 'Stopped')
        ], copy=False, default='draft')
    model_id = fields.Many2one(
        'ir.model', string='Model', index=True, required=True,
        default=lambda self: self.env.ref('base.model_res_partner', raise_if_not_found=False),
        domain="[('is_mail_thread', '=', True)]")
    model_name = fields.Char(string='Model Name', related='model_id.model', readonly=True, store=True)
    unique_field_id = fields.Many2one(
        'ir.model.fields', string='Unique Field',
        domain="[('model_id', '=', model_id), ('ttype', 'in', ['char', 'int', 'many2one', 'text', 'selection'])]",
        help="""Used to avoid duplicates based on model field.\ne.g.
                For model 'Customers', select email field here if you don't
                want to process records which have the same email address""")
    domain = fields.Char(string='Filter', default='[]')
    # activities
    marketing_activity_ids = fields.One2many('marketing.activity', 'campaign_id', string='Activities', copy=True)
    last_sync_date = fields.Datetime(string='Last activities synchronization')
    require_sync = fields.Boolean(string="Sync of participants is required", compute='_compute_require_sync')
    # participants
    participant_ids = fields.One2many('marketing.participant', 'campaign_id', string='Participants')
    running_participant_count = fields.Integer(string="# of active participants", compute='_compute_participants')
    completed_participant_count = fields.Integer(string="# of completed participants", compute='_compute_participants')
    total_participant_count = fields.Integer(string="# of active and completed participants", compute='_compute_participants')

    @api.depends('marketing_activity_ids.require_sync', 'last_sync_date')
    def _compute_require_sync(self):
        for campaign in self.filtered(lambda camp: camp.last_sync_date and camp.state == 'running'):
            activities_changed = campaign.marketing_activity_ids.filtered(lambda activity: activity.require_sync)
            campaign.require_sync = bool(activities_changed)

    @api.depends('participant_ids.state')
    def _compute_participants(self):
        participants_data = self.env['marketing.participant'].read_group(
            [('campaign_id', 'in', self.ids)],
            ['campaign_id', 'state'],
            ['campaign_id', 'state'], lazy=False)
        mapped_data = {campaign.id: {} for campaign in self}
        for data in participants_data:
            mapped_data[data['campaign_id'][0]][data['state']] = data['__count']
        for campaign in self:
            campaign_data = mapped_data.get(campaign.id)
            campaign.running_participant_count = campaign_data.get('running', 0)
            campaign.completed_participant_count = campaign_data.get('completed', 0)
            campaign.total_participant_count = campaign.completed_participant_count + campaign.running_participant_count

    def action_set_synchronized(self):
        self.write({'last_sync_date': Datetime.now()})
        self.mapped('marketing_activity_ids').write({'require_sync': False})

    def action_update_participants(self):
        """ Synchronizes all participants based campaign activities demanding synchronization
        It is done in 2 part:

         * update traces related to updated activities. This means basically recomputing the
           schedule date
         * creating new traces for activities recently added in the workflow :

          * 'begin' activities simple create new traces for all running participants;
          * other activities: create child for traces linked to the parent of the newly created activity
          * we consider scheduling to be done after parent processing, independently of other time considerations
          * for 'not' triggers take into account brother traces that could be already processed
        """
        for campaign in self:
            # Action 1: On activity modification
            modified_activities = campaign.marketing_activity_ids.filtered(lambda activity: activity.require_sync)
            traces_to_reschedule = self.env['marketing.trace'].search([
                ('state', '=', 'scheduled'),
                ('activity_id', 'in', modified_activities.ids)])
            for trace in traces_to_reschedule:
                trace_offset = relativedelta(**{trace.activity_id.interval_type: trace.activity_id.interval_number})
                trigger_type = trace.activity_id.trigger_type
                if trigger_type == 'begin':
                    trace.schedule_date = Datetime.from_string(trace.participant_id.create_date) + trace_offset
                elif trigger_type in ['act', 'mail_not_open', 'mail_not_click', 'mail_not_reply'] and trace.parent_id:
                    trace.schedule_date = Datetime.from_string(trace.parent_id.schedule_date) + trace_offset
                elif trace.parent_id:
                    process_dt = trace.parent_id.statistics_ids.state_update
                    trace.schedule_date = Datetime.from_string(process_dt) + trace_offset

            # Action 2: On activity creation
            created_activities = campaign.marketing_activity_ids.filtered(lambda a: a.create_date >= campaign.last_sync_date)
            for activity in created_activities:
                activity_offset = relativedelta(**{activity.interval_type: activity.interval_number})
                # Case 1: Trigger = begin
                # Create new root traces for all running participants -> consider campaign begin date is now to avoid spamming participants
                if activity.trigger_type == 'begin':
                    participants = self.env['marketing.participant'].search([('state', '=', 'running')])
                    for participant in participants:
                        schedule_date = Datetime.from_string(Datetime.now()) + activity_offset
                        self.env['marketing.trace'].create({
                            'activity_id': activity.id,
                            'participant_id': participant.id,
                            'schedule_date': schedule_date,
                        })
                else:
                    valid_parent_traces = self.env['marketing.trace'].search([
                        ('state', '=', 'processed'),
                        ('activity_id', '=', activity.parent_id.id)
                    ])

                    # avoid creating new traces that would have processed brother traces already processed
                    # example: do not create a mail_not_click trace if mail_click is already processed
                    if activity.trigger_type in ['mail_not_open', 'mail_not_click', 'mail_not_reply']:
                        opposite_trigger = activity.trigger_type.replace('_not_', '_')
                        brother_traces = self.env['marketing.trace'].search([
                            ('parent_id', 'in', valid_parent_traces.ids),
                            ('trigger_type', '=', opposite_trigger),
                            ('state', '=', 'processed'),
                        ])
                        valid_parent_traces = valid_parent_traces - brother_traces.mapped('parent_id')

                    valid_parent_traces.mapped('participant_id').filtered(lambda participant: participant.state == 'completed').action_set_running()

                    for parent_trace in valid_parent_traces:
                        self.env['marketing.trace'].create({
                            'activity_id': activity.id,
                            'participant_id': parent_trace.participant_id.id,
                            'parent_id': parent_trace.id,
                            'schedule_date': Datetime.from_string(parent_trace.schedule_date) + activity_offset,
                        })

        self.action_set_synchronized()

    def action_start_campaign(self):
        if any(not campaign.marketing_activity_ids for campaign in self):
            raise ValidationError(_('You must set up at least one activity to start this campaign.'))
        self.write({'state': 'running'})

    def action_stop_campaign(self):
        self.write({'state': 'stopped'})

    def sync_participants(self):
        """ Creates new participants, taking into account already-existing ones
        as well as campaign filter and unique field. """
        participants = self.env['marketing.participant']
        for campaign in self.filtered(lambda c: c.marketing_activity_ids):
            now = Datetime.from_string(Datetime.now())
            if not campaign.last_sync_date:
                campaign.last_sync_date = now

            RecordModel = self.env[campaign.model_name]

            # Fetch existing participants
            participants_data = participants.search_read([('campaign_id', '=', campaign.id)], ['res_id'])
            existing_rec_ids = set([live_participant['res_id'] for live_participant in participants_data])

            record_domain = safe_eval(campaign.domain or [])
            # check uniqueness based on 'unique_field_id' field
            if campaign.unique_field_id and campaign.unique_field_id.name != 'id':
                # Don't use browse maybe record is deleted
                existing_records = RecordModel.read(existing_rec_ids, [campaign.unique_field_id.name])
                unique_field_vals = set([rec[campaign.unique_field_id.name] for rec in existing_records])
                unique_domain = [(campaign.unique_field_id.name, 'not in', unique_field_vals)]
                record_domain = expression.AND([unique_domain, record_domain])
            db_rec_ids = set(RecordModel.search(record_domain).ids)
            to_create = db_rec_ids - existing_rec_ids
            to_remove = existing_rec_ids - db_rec_ids

            for rec_id in to_create:
                participants |= participants.create({
                    'campaign_id': campaign.id,
                    'res_id': rec_id,
                })

            if to_remove:
                participants.search([('res_id', 'in', list(to_remove))]).action_set_unlink()

        return participants

    def execute_activities(self):
        for campaign in self:
            campaign.marketing_activity_ids.execute()


class MarketingActivity(models.Model):
    _name = 'marketing.activity'
    _description = 'Marketing Activity'
    _inherits = {'utm.source': 'utm_source_id'}
    _order = 'interval_standardized'

    utm_source_id = fields.Many2one('utm.source', 'Source', ondelete='cascade', required=True)
    campaign_id = fields.Many2one(
        'marketing.campaign', string='Campaign',
        index=True, ondelete='cascade', required=True)
    interval_number = fields.Integer(string='Send after', default=1)
    interval_type = fields.Selection([
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')], string='Delay Type',
        default='hours', required=True)
    interval_standardized = fields.Integer('Send after (in hours)', compute='_compute_interval_standardized', store=True, readonly=True)

    validity_duration = fields.Boolean('Validity Duration')
    validity_duration_number = fields.Integer(string='Valid during', default=0)
    validity_duration_type = fields.Selection([
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')],
        default='hours', required=True)

    require_sync = fields.Boolean('Require trace sync')

    domain = fields.Char(
        string='Filter', default='[]',
        help='Activity will only be performed if record satisfies this domain')
    model_id = fields.Many2one('ir.model', related='campaign_id.model_id', string='Model', readonly=True)
    model_name = fields.Char(related='campaign_id.model_id.model', string='Model Name', readonly=True)

    activity_type = fields.Selection([
        ('email', 'Email'),
        ('action', 'Server Action')
        ], required=True, default='email')
    mass_mailing_id = fields.Many2one('mail.mass_mailing', string='Email Template')
    server_action_id = fields.Many2one('ir.actions.server', string='Server Action')

    # Related to parent activity
    parent_id = fields.Many2one(
        'marketing.activity', string='Activity',
        index=True, ondelete='cascade')
    child_ids = fields.One2many('marketing.activity', 'parent_id', string='Child Activities')
    trigger_type = fields.Selection([
        ('begin', 'beginning of campaign'),
        ('act', 'another activity'),
        ('mail_open', 'Mail: opened'),
        ('mail_not_open', 'Mail: not opened'),
        ('mail_reply', 'Mail: replied'),
        ('mail_not_reply', 'Mail: not replied'),
        ('mail_click', 'Mail: clicked'),
        ('mail_not_click', 'Mail: not clicked'),
        ('mail_bounce', 'Mail: bounced')], default='begin', required=True)

    # For trace
    trace_ids = fields.One2many('marketing.trace', 'activity_id', string='Traces')
    processed = fields.Integer(compute='_compute_statistics')
    rejected = fields.Integer(compute='_compute_statistics')
    total_sent = fields.Integer(compute='_compute_statistics')
    total_click = fields.Integer(compute='_compute_statistics')
    total_open = fields.Integer(compute='_compute_statistics')
    total_reply = fields.Integer(compute='_compute_statistics')
    total_bounce = fields.Integer(compute='_compute_statistics')
    statistics_graph_data = fields.Char(compute='_compute_statistics_graph_data')

    @api.depends('interval_type', 'interval_number')
    def _compute_interval_standardized(self):
        factors = {'hours': 1,
                   'days': 24,
                   'weeks': 168,
                   'months': 720}
        for activity in self:
            activity.interval_standardized = activity.interval_number * factors[activity.interval_type]

    @api.depends('activity_type', 'trace_ids')
    def _compute_statistics(self):
        if not self.ids:
            self.update({
                'total_bounce': 0, 'total_reply': 0, 'total_sent': 0,
                'rejected': 0, 'total_click': 0, 'processed': 0, 'total_open': 0,
            })
        else:
            activity_data = {activity.id: {} for activity in self}
            for stat in self._get_full_statistics():
                activity_data[stat.pop('activity_id')].update(stat)
            for activity in self:
                activity.update(activity_data[activity.id])

    @api.depends('activity_type', 'trace_ids')
    def _compute_statistics_graph_data(self):
        if not self.ids:
            date_range = [date.today() - timedelta(days=d) for d in range(0, 15)]
            date_range.reverse()
            default_values = [{'x': date_item.strftime('%d %b'), 'y': 0} for date_item in date_range]
            self.statistics_graph_data = json.dumps([
                {'values': default_values, 'key': _('Success'), 'area': True, 'color': '#21B799'},
                {'values': default_values, 'key': _('Rejected'), 'arzea': True, 'color': '#d9534f'}])
        else:
            activity_data = {activity.id: {} for activity in self}
            for act_id, graph_data in self._get_graph_statistics().items():
                activity_data[act_id]['statistics_graph_data'] = json.dumps(graph_data)
            for activity in self:
                activity.update(activity_data[activity.id])

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if any(not activity._check_recursion() for activity in self):
            raise ValidationError(_("Error! You can't create recursive hierarchy of Activity."))

    @api.constrains('trigger_type', 'parent_id')
    def _check_trigger_begin(self):
        if any(activity.trigger_type == 'begin' and activity.parent_id for activity in self):
            raise ValidationError(_("Error! You can't define a child activity with a trigger of type 'begin'."))

    @api.model
    def create(self, values):
        campaign_id = values.get('campaign_id')
        if not campaign_id:
            campaign_id = self.default_get(['campaign_id'])['campaign_id']
        values['require_sync'] = self.env['marketing.campaign'].browse(campaign_id).state == 'running'
        return super(MarketingActivity, self).create(values)

    def write(self, values):
        if any(field in values.keys() for field in ('interval_number', 'interval_type')):
            values['require_sync'] = True
        return super(MarketingActivity, self).write(values)

    def _get_full_statistics(self):
        self.env.cr.execute("""
            SELECT
                trace.activity_id,
                COUNT(CASE WHEN stat.bounced IS NULL THEN 1 ELSE null END) AS total_sent,
                COUNT(CASE WHEN stat.clicked IS NOT NULL THEN 1 ELSE null END) AS total_click,
                COUNT(CASE WHEN stat.replied IS NOT NULL THEN 1 ELSE null END) AS total_reply,
                COUNT(CASE WHEN stat.opened IS NOT NULL THEN 1 ELSE null END) AS total_open,
                COUNT(CASE WHEN stat.bounced IS NOT NULL THEN 1 ELSE null END) AS total_bounce,
                COUNT(CASE WHEN trace.state = 'processed' THEN 1 ELSE null END) AS processed,
                COUNT(CASE WHEN trace.state = 'rejected' THEN 1 ELSE null END) AS rejected
            FROM
                marketing_trace AS trace
            JOIN
                mail_mail_statistics AS stat
                ON (stat.marketing_trace_id = trace.id)
            JOIN
                marketing_participant AS part
                ON (trace.participant_id = part.id)
            WHERE
                trace.activity_id IN %s
            GROUP BY
                trace.activity_id;
        """, (tuple(self.ids), ))
        return self.env.cr.dictfetchall()

    def _get_graph_statistics(self):
        """ Compute activities statistics based on their traces state for the last fortnight """
        past_date = (Datetime.from_string(Datetime.now()) + timedelta(days=-14)).strftime('%Y-%m-%d 00:00:00')
        stat_map = {}
        base = date.today() + timedelta(days=-14)
        date_range = [base + timedelta(days=d) for d in range(0, 15)]

        self.env.cr.execute("""
            SELECT
                activity.id AS activity_id,
                trace.schedule_date::date AS dt,
                count(*) AS total,
                trace.state
            FROM
                marketing_trace AS trace
            JOIN
                marketing_activity AS activity
                ON (activity.id = trace.activity_id)
            WHERE activity.id IN %s AND trace.schedule_date >= %s
            GROUP BY activity.id , dt, trace.state
            ORDER BY dt;
        """, (tuple(self.ids), past_date))

        for stat in self.env.cr.dictfetchall():
            stat_map[(stat['activity_id'], stat['dt'], stat['state'])] = stat['total']

        graph_data = {}
        for activity in self:
            success = []
            rejected = []
            for i in date_range:
                x = i.strftime('%d %b')
                success.append({
                    'x': x,
                    'y': stat_map.get((activity.id, i.strftime('%Y-%m-%d'), 'processed'), 0)
                })
                rejected.append({
                    'x': x,
                    'y': stat_map.get((activity.id, i.strftime('%Y-%m-%d'), 'rejected'), 0)
                })
            graph_data[activity.id] = [
                {'values': success, 'key': _('Success'), 'area': True, 'color': '#21B799'},
                {'values': rejected, 'key': _('Rejected'), 'area': True, 'color': '#d9534f'}
            ]
        return graph_data

    def execute(self, domain=None):
        trace_domain = [
            ('schedule_date', '<=', Datetime.now()),
            ('state', '=', 'scheduled'),
            ('activity_id', 'in', self.ids),
            ('participant_id.state', '=', 'running'),
        ]
        if domain:
            trace_domain += domain

        traces = self.env['marketing.trace'].search(trace_domain)

        # organize traces by activity
        trace_to_activities = dict()
        for trace in traces:
            if trace.activity_id not in trace_to_activities:
                trace_to_activities[trace.activity_id] = trace
            else:
                trace_to_activities[trace.activity_id] |= trace

        # execute activity on their traces
        for activity, traces in trace_to_activities.items():
            activity.execute_on_traces(traces)

    def execute_on_traces(self, traces):
        """ Execute current activity on given traces.

        :param traces: record set of traces on which the activity should run
        """
        self.ensure_one()
        new_traces = self.env['marketing.trace']

        if self.validity_duration:
            duration = relativedelta(**{self.validity_duration_type: self.validity_duration_number})
            invalid_traces = traces.filtered(lambda trace: not trace.schedule_date or trace.schedule_date + duration < Datetime.now())
            invalid_traces.action_cancel()
            traces = traces - invalid_traces

        # Filter traces not fitting the activity filter and whose record has been deleted
        if self.domain:
            rec_domain = expression.AND([safe_eval(self.campaign_id.domain), safe_eval(self.domain)])
        else:
            rec_domain = safe_eval(self.campaign_id.filter)
        if rec_domain:
            rec_valid = self.env[self.model_name].search(rec_domain)
            rec_ids_domain = set(rec_valid.ids)

            traces_allowed = traces.filtered(lambda trace: trace.res_id in rec_ids_domain)
            traces_rejected = traces.filtered(lambda trace: trace.res_id not in rec_ids_domain)  # either rejected, either deleted record
        else:
            traces_allowed = traces
            traces_rejected = self.env['marketing.trace']

        if traces_allowed:
            activity_method = getattr(self, '_execute_%s' % (self.activity_type))
            activity_method(traces_allowed)
            new_traces |= self._generate_children_traces(traces_allowed)
            traces.mapped('participant_id').check_completed()

        if traces_rejected:
            traces_rejected.write({
                'state': 'rejected',
                'state_msg': _('Rejected by activity filter or record deleted / archived')
            })

        return new_traces

    def _execute_action(self, traces):
        if not self.server_action_id:
            return False

        # Do a loop here because we have to try / catch each execution separately to ensure other traces are executed
        # and proper state message stored
        traces_ok = self.env['marketing.trace']
        for trace in traces:
            action = self.server_action_id.with_context(
                active_model=self.model_name,
                active_ids=[trace.res_id],
                active_id=trace.res_id,
            )
            try:
                action.run()
            except Exception as e:
                _logger.warning(_('Marketing Automation: activity <%s> encountered server action issue %s'), self.id, str(e), exc_info=True)
                trace.write({
                    'state': 'error',
                    'schedule_date': Datetime.now(),
                    'state_msg': _('Exception in server action: %s') % e.message,
                })
            else:
                traces_ok |= trace

        # Update status
        traces_ok.write({
            'state': 'processed',
            'schedule_date': Datetime.now(),
        })
        return True

    def _execute_email(self, traces):
        res_ids = [r for r in set(traces.mapped('res_id'))]

        mailing = self.mass_mailing_id.with_context(
            default_marketing_activity_id=self.ids[0],
            active_ids=res_ids,
        )

        try:
            mailing.send_mail(res_ids)
        except Exception as e:
            _logger.warning(_('Marketing Automation: activity <%s> encountered mass mailing issue %s'), self.id, str(e), exc_info=True)
            traces.write({
                'state': 'error',
                'schedule_date': Datetime.now(),
                'state_msg': _('Exception in mass mailing: %s') % e.message,
            })
        else:
            traces.write({
                'state': 'processed',
                'schedule_date': Datetime.now(),
            })
        return True

    def _generate_children_traces(self, traces):
        """Generate child traces for child activities and compute their schedule date except for mail_open,
        mail_click, mail_reply, mail_bounce which are computed when processing the mail event """
        child_traces = self.env['marketing.trace']
        for activity in self.child_ids:
            activity_offset = relativedelta(**{activity.interval_type: activity.interval_number})

            for trace in traces:
                vals = {
                    'parent_id': trace.id,
                    'participant_id': trace.participant_id.id,
                    'activity_id': activity.id
                }
                if activity.trigger_type in ['act', 'mail_not_open', 'mail_not_click', 'mail_not_reply']:
                    vals['schedule_date'] = Datetime.from_string(trace.schedule_date) + activity_offset
                child_traces |= child_traces.create(vals)

        return child_traces
