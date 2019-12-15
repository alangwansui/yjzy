# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import Warning

class account_journal(models.Model):
    _inherit = 'account.journal'

    type = fields.Selection(selection_add=[('renling', u'认领')])