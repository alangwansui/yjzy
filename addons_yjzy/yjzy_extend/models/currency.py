# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from datetime import datetime, timedelta, date



class Currency(models.Model):
    _inherit = 'res.currency'
    rate = fields.Float(compute='_compute_current_rate', string='Current Rate', digits=(12, 8),
                        help='The rate of the currency to the currency of rate 1.')