# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning


class res_company(models.Model):
    _inherit = 'res.company'

    full_name = fields.Char(u'公司全称', translate=True)
    fax = fields.Char(u'传真')

    purchase_image = fields.Binary(u'采购合同章', widget='image')
    sale_image = fields.Binary(u'销售合同章', widget='image')



