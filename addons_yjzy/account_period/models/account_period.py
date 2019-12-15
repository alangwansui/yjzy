# -*- coding: utf-8 -*-
# Copyright 2017 Jarvis (www.odoomod.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import odoo
from odoo import api, models, _, fields, osv
from odoo.osv import expression


class AccountPeriod(models.Model):
    _name = "account.period"
    _description = "Account period"
    _order = "date_start, special desc"

    name = fields.Char('Period Name', required=True)
    code = fields.Char('Code', size=12)
    special = fields.Boolean('Opening/Closing Period', help="These periods can overlap.")
    date_start = fields.Date('Start of Period', required=True, states={'done': [('readonly', True)]})
    date_stop = fields.Date('End of Period', required=True, states={'done': [('readonly', True)]})
    fiscalyear_id = fields.Many2one('account.fiscalyear', 'Fiscal Year', required=True,
                                    states={'done': [('readonly', True)]}, index=True)
    state = fields.Selection([('draft', 'Open'), ('done', 'Closed')], 'Status', readonly=True, copy=False,
                             default='draft',
                             help='When monthly periods are created. The status is \'Draft\'. At the end of monthly period it is in \'Done\' status.')
    company_id = fields.Many2one('res.company', related='fiscalyear_id.company_id', string='Company', store=True,
                                 readonly=True)

    @api.multi
    def action_draft(self):
        mode = 'draft'
        for period in self:
            if period.fiscalyear_id.state == 'done':
                raise osv.except_osv(_('Warning!'), _('You can not re-open a period which belongs to closed fiscal year'))
        #self.env.cr.execute('update account_journal_period set state=%s where period_id in %s', (mode, tuple(self.ids),))
        self.env.cr.execute('update account_period set state=%s where id in %s', (mode, tuple(self.ids),))
        return True