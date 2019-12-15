# -*- coding: utf-8 -*-
##############################################################################
from odoo import api, fields, models, _
from odoo.models import BaseModel as BM
from . import tools

BM.collect_hs_lines = tools.collect_hs_lines


