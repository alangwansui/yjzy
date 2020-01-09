# -*- coding: utf-8 -*-
import logging
from odoo import _, api, models

_logger = logging.getLogger(__name__)


@api.model
def get_categories(self):
    # dbdata = self.search([], order="parent_id")
    # data = [{'id': d.id, 'pid': d.parent_id.id, 'name': d.name} for d in dbdata]
    data = []
    return {'do_flag': False,
            'field': 'category field',
            'title': _('my category'),
            'data': data
            }


models.BaseModel.get_categories = get_categories


class Product(models.Model):
    _inherit = "product.template"

    @api.model
    def get_categories(self):
        dbdata = self.env['product.category'].search([])
        data = [{'id': d.id, 'pid': d.parent_id.id, 'name': d.name} for d in dbdata]
        return {'do_flag': True,
                'field': 'categ_id',
                'title': '产品类别',
                'data': data
                }



class mail_message(models.Model):
    _inherit = "mail.message"

    @api.model
    def get_categories(self):
        dbdata = self.env['res.partner'].search([])
        data = [{'id': d.id, 'pid': d.parent_id.id, 'name': d.name} for d in dbdata]
        return {'do_flag': True,
                'field': 'partner_ids',
                'title': '客户',
                'data': data
                }