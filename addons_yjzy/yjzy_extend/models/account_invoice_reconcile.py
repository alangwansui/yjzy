# -*- coding: utf-8 -*-
from odoo import models, tools, fields, api, _
from odoo.exceptions import Warning, UserError
from odoo.tools import float_is_zero, float_compare
from .comm import sfk_type
import logging

_logger = logging.getLogger(__name__)


# 注意：直接单独创建应付申请，和预付认领的时候，默认状态需要注意

class account_reconcile_order(models.Model):
    _inherit = 'account.invoice'

    # 创建核销单
    def create_reconcile(self):
        if len(self.payment_log_ids.filtered(lambda x: x.state not in ['posted', 'reconciled'])) > 0:
            raise Warning('存在未审批完成的核销单，不允许再次创建')
        form_view = self.env.ref('yjzy_extend.view_ysrld_reconcile_form')
        ctx = {}
        partner = self.partner_id
        if self.type == 'out_invoice' and self.yjzy_type_1 != 'back_tax':
            # partner = self.env['res.partner'].search([('name', '=', u'未定义')], limit=1)
            ctx = {
                'show_shoukuan': True,
                'default_sfk_type': 'reconcile_yingshou',
                'default_payment_type': 'inbound',
                'default_be_renling': True,
                'default_advance_ok': False,
                'default_partner_type': 'customer',
                'default_partner_id': partner.id,
                'default_invoice_log_id': self.id,
                'default_payment_method_id': 2,
                'default_currency_id': self.currency_id.id,
                'default_invoice_ids': [(4, self.id, None)],
                'default_reconcile_type': '50_reconcile',
                'default_invoice_log_id_this_time': self.residual,
                'default_fault_comments': self.fault_comments,

            }
        if self.type == 'out_invoice' and self.yjzy_type_1 == 'back_tax':
            ctx = {'show_shoukuan': True,
                   'default_sfk_type': 'reconcile_tuishui',
                   'default_payment_type': 'outbound',
                   'default_be_renling': True,
                   'default_advance_ok': False,
                   'default_partner_type': 'supplier',
                   'default_partner_id': partner.id,
                   'default_invoice_log_id': self.id,
                   'default_payment_method_id': 2,
                   'default_currency_id': self.currency_id.id,
                   'default_invoice_ids': [(4, self.id, None)],
                   'default_reconcile_type': '50_reconcile',
                   'default_invoice_log_id_this_time': self.residual,
                   'default_fault_comments': self.fault_comments
                   }

        if self.type == 'in_invoice':
            ctx = {'show_shoukuan': True,
                   'default_sfk_type': 'reconcile_yingfu',
                   'default_payment_type': 'outbound',
                   'default_be_renling': True,
                   'default_advance_ok': False,
                   'default_partner_type': 'supplier',
                   'default_partner_id': partner.id,
                   'default_invoice_log_id': self.id,
                   'default_payment_method_id': 2,
                   'default_currency_id': self.currency_id.id,
                   'default_invoice_ids': [(4, self.id, None)],
                   'default_reconcile_type': '50_reconcile',
                   'default_invoice_log_id_this_time': self.residual,
                   'default_fault_comments': self.fault_comments
                   }

        return {
            'name': u'核销单',
            'view_type': 'form',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'views': [(form_view.id, 'form')],
            'target': 'current',
            'context': ctx
        }
