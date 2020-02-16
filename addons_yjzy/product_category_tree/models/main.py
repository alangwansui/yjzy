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
        no_show_tree_keys = self.env.context.get('no_show_tree_keys', [])

        print('===========', no_show_tree_keys )

        if self._name == 'mail.message':
            data_tmp = [
                {'id': 'newmail', 'pid': None, 'name': '写邮件', 'no_action': True, 'nocheck': True},
                {'id': 'mail_list_income', 'pid': None, 'name': '收件箱', 'checked': True,  'no_action': False,'special_domain': [('process_type', '=', 'in')]},
                {'id': 'mail_list_out', 'pid': None, 'name': '发件箱', 'checked': True, 'no_action': False,'special_domain': [('process_type', '!=', 'in')]},
                #{'id': 'mail_list_recycle', 'pid': None, 'name': '回收站', 'no_action': False, 'nocheck': True, 'special_domain': [('message_type', '=', 'email'), ('state_delete', '=', 'recycle')]},
                #{'id': 'mail_list_deleted', 'pid': None, 'name': '已删除', 'no_action': False,'special_domain': [('message_type', '=', 'email'), ('active', '=', False)]},
                #{'id': 'mail_list_draft', 'pid': None, 'name': '草稿箱', 'no_action': False,'special_domain': [('message_type', '=', 'email')]},
                {'id': 'customer', 'pid': None, 'name': '客户', 'no_action': True, 'nocheck': True},
                {'id': 'supplier', 'pid': None, 'name': '供应商', 'no_action': True, 'nocheck': True},
                {'id': 'personal', 'pid': None, 'name': '个人通讯录', 'no_action': True, 'nocheck': True},
                {'id': 'user', 'pid': None, 'name': '用户', 'no_action': True, 'nocheck': True},

               # {'id': 'mail_list', 'pid': None, 'name': '邮件列表', 'no_action': True},

            ]

            data = []
            for d in data_tmp:
                if not (d['id'] in no_show_tree_keys):
                    data.append(d)

            customers = self.env['res.partner'].search([('customer', '=', True)])
            suppliers = self.env['res.partner'].search([('supplier', '=', True)])
            personals = self.env['personal.partner'].search([('tag_id.code','=','normal')])
            users = self.env.user.sub_message_uids ###| self.env['res.users'].search([('leader_user_id','=', self._uid)])


            data += [{'dbid': d.id, 'id': 'c_%s' % d.id, 'pid': d.parent_id and 'c_%s' % d.parent_id.id or 'customer', 'name': d.name, 'model': 'res.partner'} for d in customers]
            data += [{'dbid': d.id, 'id': 's_%s' % d.id, 'pid': d.parent_id and 's_%s' % d.parent_id.id or 'supplier', 'name': d.name, 'model': 'res.partner'} for d in suppliers]
            data += [{'dbid': d.id, 'id': 'p_%s' % d.id, 'pid':'personal', 'name': d.name, 'model': 'personal.partner', 'domain_fd': 'all_personal_ids'} for d in personals]

            if not 'user' in no_show_tree_keys:
                data += [{'dbid': d.id, 'id': 'u_%s' % d.id, 'pid': 'user', 'name': d.name, 'model': 'res.users', 'domain_fd': 'all_user_ids'} for d in users]





            return {
                'do_flag': True,
                'field': 'all_partner_ids',
                'title': '通讯录',
                'data': data
            }
        else:
            ## 草稿箱
            data = [
                {'id': 'newmail', 'pid': None, 'name': '写邮件', 'no_action': True, 'nocheck': True},
                #{'id': 'mail_list_income', 'pid': None, 'name': '收件箱', 'checked': True,  'no_action': False,'special_domain': [('state_delete', '!=', 'recycle'),('alias_user_id','=', self._uid ),('message_type', '=', 'email'), ('process_type', '=', 'in')]},
                #{'id': 'mail_list_out', 'pid': None, 'name': '发件箱', 'checked': True, 'no_action': False,'special_domain': [('state_delete', '!=', 'recycle'),('author_id.user_ids','=', self._uid),('message_type', '=', 'email'), ('process_type', '=', False)]},
                #{'id': 'mail_list_recycle', 'pid': None, 'name': '回收站', 'no_action': False, 'nocheck': True, 'special_domain': [('message_type', '=', 'email'), ('state_delete', '=', 'recycle')]},
                #{'id': 'mail_list_deleted', 'pid': None, 'name': '已删除', 'no_action': False,'special_domain': [('message_type', '=', 'email'), ('active', '=', False)]},
                #{'id': 'mail_list_draft', 'pid': None, 'name': '草稿箱', 'no_action': False,'special_domain': [('message_type', '=', 'email')]},
                {'id': 'customer', 'pid': None, 'name': '客户', 'no_action': True, 'nocheck': True},
                {'id': 'supplier', 'pid': None, 'name': '供应商', 'no_action': True, 'nocheck': True},
                {'id': 'personal', 'pid': None, 'name': '个人通讯录', 'no_action': True, 'nocheck': True},
                #{'id': 'user', 'pid': None, 'name': '用户', 'no_action': True, 'nocheck': True},
               # {'id': 'mail_list', 'pid': None, 'name': '邮件列表', 'no_action': True},
            ]

            customers = self.env['res.partner'].search([('customer', '=', True)])
            suppliers = self.env['res.partner'].search([('supplier', '=', True)])
            personals = self.env['personal.partner'].search([('tag_id.code','=','normal')])
            data += [{'dbid': d.id, 'id': 'c_%s' % d.id, 'pid': d.parent_id and 'c_%s' % d.parent_id.id or 'customer', 'name': d.name, 'model': 'res.partner'} for d in customers]
            data += [{'dbid': d.id, 'id': 's_%s' % d.id, 'pid': d.parent_id and 's_%s' % d.parent_id.id or 'supplier', 'name': d.name, 'model': 'res.partner'} for d in suppliers]
            data += [{'dbid': d.id, 'id': 'p_%s' % d.id, 'pid':'personal', 'name': d.name, 'model': 'personal.partner', 'domain_fd': 'all_personal_ids'} for d in personals]


            return {'do_flag': True,
                    'field': 'category field',
                    'title': _('my category'),
                    'data': data
                    }