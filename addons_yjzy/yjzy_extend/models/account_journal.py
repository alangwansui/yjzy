# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import Warning

class account_journal(models.Model):
    _inherit = 'account.journal'

    type = fields.Selection(selection_add=[('renling', u'认领')])
    gongsi_id = fields.Many2one('gongsi',u'公司主体')

    def name_get(self):
        res = []
        for one in self:
            name = '%s:%s' % (one.name,one.company_id.name)
            res.append((one.id, name))
        return res