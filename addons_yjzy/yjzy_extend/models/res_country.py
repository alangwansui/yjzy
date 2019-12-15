# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning


class CountryState(models.Model):

    _inherit = 'res.country.state'

    name = fields.Char(string='State Name', required=True, translate=True,
               help='Administrative divisions of a country. E.g. Fed. State, Departement, Canton')