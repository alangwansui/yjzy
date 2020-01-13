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
        data = [
            {'id': 'customer', 'pid': None, 'name': '客户', 'no_action': True},
            {'id': 'supplier', 'pid': None, 'name': '供应商', 'no_action': True},
            {'id': 'personal', 'pid': None, 'name': '个人通讯录', 'no_action': True},
            {'id': 'mail_list', 'pid': None, 'name': '邮件列表', 'no_action': True},
            {'id': 'mail_list_income', 'pid': 'mail_list', 'name': '收件箱', 'no_action': False, 'special_domain': [('process_type','=', 'in')]},
            {'id': 'mail_list_out', 'pid': 'mail_list', 'name': '发件箱', 'no_action': False, 'special_domain': [('process_type','!=', 'in' )]},
        ]

        customers = self.env['res.partner'].search([('customer', '=', True), ('parent_id', '=', False)])
        suppliers = self.env['res.partner'].search([('supplier', '=', True), ('parent_id', '=', False)])

        personals = self.env['res.partner'].search([('supplier', '=', False), ('customer', '=', False), ('parent_id', '=', False)])

        data += [{'id': d.id, 'pid': 'customer', 'name': d.name} for d in customers]
        data += [{'id': d.id, 'pid': 'supplier', 'name': d.name} for d in suppliers]
        data += [{'id': d.id, 'pid': 'personal', 'name': d.name} for d in personals]

        return {
            'do_flag': True,
            'field': 'partner_ids',
            'title': '客户',
            'data': data
        }
