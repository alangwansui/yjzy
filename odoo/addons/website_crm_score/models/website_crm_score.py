# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.tools.safe_eval import safe_eval
from odoo.osv.expression import expression
import datetime
import logging


_logger = logging.getLogger(__name__)
evaluation_context = {
    'datetime': datetime,
    'context_today': datetime.datetime.now,
}


class website_crm_score(models.Model):
    _name = 'website.crm.score'
    _inherit = ['mail.thread']

    @api.one
    def _count_leads(self):
        if self.id:
            self._cr.execute("""
                 SELECT COUNT(1)
                 FROM crm_lead_score_rel
                 WHERE score_id = %s
                 """, (self.id,))
            self.leads_count = self._cr.fetchone()[0]
        else:
            self.leads_count = 0

    @api.one
    @api.constrains('domain')
    def _assert_valid_domain(self):
        try:
            domain = safe_eval(self.domain or '[]', evaluation_context)
            self.env['crm.lead'].search(domain, limit=1)
        except Exception as e:
            _logger.warning('Exception: %s' % (e,))
            raise Warning('The domain is incorrectly formatted')

    name = fields.Char('Name', required=True)
    rule_type = fields.Selection([('score', 'Scoring'), ('active', 'Archive'), ('unlink', 'Delete')], default='score', required=True, track_visibility='onchange',
                                 help='Scoring will add a score of `value` for this lead.\n'
                                 'Archive will set active = False on the lead (archived)\n'
                                 'Delete will delete definitively the lead\n\n'
                                 'Actions are done in sql and bypass the access rights and orm mechanism (create `score`, write `active`, unlink `crm_lead`)')
    value = fields.Float('Value', default=0, required=True, track_visibility='onchange')
    domain = fields.Char('Domain', track_visibility='onchange', required=True)
    event_based = fields.Boolean(
        'Event-based rule',
        help='When checked, the rule will be re-evaluated every time, even for leads '
             'that have already been checked previously. This option incurs a large '
             'performance penalty, so it should be checked only for rules that depend '
             'on dynamic events',
        default=False, track_visibility='onchange'
    )
    running = fields.Boolean('Active', default=True, track_visibility='onchange')
    leads_count = fields.Integer(compute='_count_leads')
    last_run = fields.Datetime('Last run', help='Date from the last scoring on all leads.')

    @api.model
    def assign_scores_to_leads(self, ids=False, lead_ids=False):
        _logger.info('Start scoring for %s rules and %s leads' % (ids and len(ids) or 'all', lead_ids and len(lead_ids) or 'all'))
        domain = [('running', '=', True)]
        if ids:
            domain.append(('id', 'in', ids))
        scores = self.search(domain)

        # Sort rule to unlink before scoring
        priorities = dict(unlink=1, active=2, score=3)
        scores = sorted(scores, key=lambda k: priorities.get(k['rule_type']))

        for score in scores:
            now = datetime.datetime.now()
            domain = safe_eval(score.domain, evaluation_context)

            # Don't replace the domain with a 'not in' like below... that doesn't make the same thing !!!
            # domain.extend(['|', ('stage_id.on_change', '=', False), ('stage_id.probability', 'not in', [0,100])])
            domain.extend(['|', ('stage_id.on_change', '=', False), '&', ('stage_id.probability', '!=', 0), ('stage_id.probability', '!=', 100)])

            e = expression(domain, self.env['crm.lead'])
            where_clause, where_params = e.to_sql()

            where_clause += """ AND (id NOT IN (SELECT lead_id FROM crm_lead_score_rel WHERE score_id = %s)) """
            where_params.append(score.id)

            if not self.event_based and not lead_ids:
                if score.last_run:
                    # Only check leads that are newer than the last matching lead.
                    where_clause += """ AND (create_date > %s) """
                    where_params.append(score.last_run)

            if lead_ids:
                where_clause += """ AND (id in %s) """
                where_params.append(tuple(lead_ids))

            if score.rule_type == 'score':
                self._cr.execute("""INSERT INTO crm_lead_score_rel
                                    SELECT crm_lead.id as lead_id, %s as score_id
                                    FROM crm_lead
                                    WHERE %s RETURNING lead_id""" % (score.id, where_clause), where_params)
                # Force recompute of fields that depends on score_ids
                returning_ids = [resp[0] for resp in self._cr.fetchall()]
                leads = self.env["crm.lead"].browse(returning_ids)
                leads.modified(['score_ids'])
                leads.recompute()
            elif score.rule_type == 'unlink':
                self._cr.execute("DELETE FROM crm_lead WHERE %s" % where_clause, where_params)
            elif score.rule_type == 'active':
                self._cr.execute("UPDATE crm_lead set active = 'f' WHERE %s" % where_clause, where_params)

            if not (lead_ids or ids):  # if global scoring
                score.last_run = now

        _logger.info('End scoring')
