# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import fields, models, api, exceptions
from odoo.tools.translate import _

class account_period_close(models.TransientModel):
    """
        close period
    """
    _name = "account.period.close"
    _description = "period close"

    sure = fields.Boolean('Check this box')

    @api.multi
    def data_save(self):
        """
        This function close period
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: account period close’s ID or list of IDs
         """
        #journal_period_pool = self.env['account.journal.period']
        #period_pool = self.env['account.period']
        account_move_obj = self.env['account.move']

        mode = 'done'
        for form in self:
            if form.sure:
                for id in self.env.context['active_ids']:
                    account_move_ids = account_move_obj.search([('period_id', '=', id), ('state', '=', "draft")])
                    if account_move_ids:
                        raise exceptions.except_orm(_('Invalid Action!'), _('In order to close a period, you must first post related journal entries.'))

                    #self.env.cr.execute('update account_journal_period set state=%s where period_id=%s', (mode, id))
                    self.env.cr.execute('update account_period set state=%s where id=%s', (mode, id))


        return {'type': 'ir.actions.act_window_close'}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
