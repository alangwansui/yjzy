# -*- coding: utf-8 -*-
import pytz
from datetime import datetime, timedelta, date
from odoo.exceptions import Warning
from odoo.tools.safe_eval import safe_eval
from odoo import models, fields, api
from jinja2 import Template
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
import logging


class user_menu(models.Model):
    _name = 'user.menu'

    hr_expense_ids = fields.One2many('hr.expense', 'user_menu_id','费用明细')

