# -*- coding: utf-8 -*-
from num2words import num2words
from odoo.addons import decimal_precision as dp
from odoo import models, fields, api, _
from odoo.exceptions import Warning
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF




class UsdPool(models.Model):

    _name = "usd.pool"
    _description = "USD Pool"
    _order = 'sequence'

    def compute_info(self):
        for one in self:
            tb_sale_amount = 0 #um(one.tb_ids.filtered(lambda x: x.state == 'approve').mapped('org_sale_amount')) #总的出运单的销售金额
            invoice_sale_amount = sum(one.invoice_ids.filtered(lambda x: x.state in ['paid','open']).mapped('yjzy_total'))#总的发票的销售金额
            tb_declare_amount =0 #sum(one.tb_ids.filtered(lambda x: x.state == 'approve').mapped('ciq_amount'))
            invoice_declare_amount = sum(one.invoice_ids.filtered(lambda x: x.state in ['paid','open']).mapped('declare_amount_total'))

            invoice_all_usd_amount_org = sum(one.invoice_ids.filtered(lambda x: x.state in ['paid','open']).mapped('all_usd_amount_org'))

            sale_receivable_amount = 0.0
            declare_amount = 0.0
            payment_amount = 0.0
            payment_sale_diff = False
            payment_sale_diff_amount = 0.0
            usd_pool_1 = 0.0
            usd_pool_2 = 0.0
            usd_pool_3 = 0.0
            usd_pool_4 = 0.0
            usd_pool = 0.0
            if one.state == '10_unlock':
                sale_receivable_amount = tb_sale_amount
                declare_amount = tb_declare_amount
                usd_pool_1 = sale_receivable_amount - declare_amount
                usd_pool = usd_pool_1
            else:
                sale_receivable_amount = invoice_sale_amount
                declare_amount = invoice_declare_amount
                payment_amount = invoice_all_usd_amount_org
                payment_sale_diff_amount = sale_receivable_amount- payment_amount
                if one.state == '20_unpaid':
                    usd_pool_2 = sale_receivable_amount - declare_amount
                    usd_pool = usd_pool_2
                elif one.state == '30_paid':
                    usd_pool_3 = payment_amount - declare_amount
                    usd_pool = usd_pool_3
                    payment_sale_diff = '10_greater_100'
                elif one.state == '40_paid':
                    usd_pool_3 = sale_receivable_amount - declare_amount
                    usd_pool = usd_pool_3
                    payment_sale_diff = '20_less_100'
                else:
                    usd_pool_4 = payment_amount
                    usd_pool = usd_pool_4

            one.sale_receivable_amount = sale_receivable_amount
            one.declare_amount = declare_amount
            one.payment_amount = payment_amount
            one.usd_pool_1 = usd_pool_1
            one.usd_pool_2 = usd_pool_2
            one.usd_pool_3 = usd_pool_3
            one.usd_pool_4 = usd_pool_4
            one.usd_pool = usd_pool
            one.payment_sale_diff_amount = payment_sale_diff_amount
            one.payment_sale_diff = payment_sale_diff





    name = fields.Char('State Name')
    sequence = fields.Integer(help="Used to order the note stages", default=1)
    tb_ids = fields.One2many('transport.bill','usd_pool_id',u'出运合同',domain=[('state','=','approve')])
    invoice_ids = fields.One2many('account.invoice','usd_pool_id',u'账单发票')
    state = fields.Selection([('10_unlock',u'未锁定'),
                              ('20_unpaid',u'已锁定未收款'),
                              ('30_paid',u'已收款大于100'),
                              ('40_paid',u'已收款小于100'),
                              ('50_no_sale_order',u'非订单收款')],'状态')
    sale_receivable_amount = fields.Float(u'销售应收',compute=compute_info)
    declare_amount = fields.Float(u'报关金额',compute=compute_info)
    payment_amount = fields.Float(u'收款',compute=compute_info)
    payment_sale_diff = fields.Selection([('10_greater_100',u'大于100'),
                              ('20_less_100',u'小于100')],u'收款差额属性',compute=compute_info)
    payment_sale_diff_amount = fields.Float(u'收款差额',compute=compute_info)
    usd_pool_1 = fields.Float(u'美金池1',compute=compute_info)
    usd_pool_2 = fields.Float(u'美金池2',compute=compute_info)
    usd_pool_3 = fields.Float(u'美金池3',compute=compute_info)
    usd_pool_4 = fields.Float(u'美金池4',compute=compute_info)
    usd_pool = fields.Float(u'美金池汇总',compute=compute_info)

    def open_transport_bill_usd_pool(self):
        self.ensure_one()
        #form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.view_transport_bill_usd_pool')
        for one in self:
            return {
                'name': u'未锁定美金池',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'transport.bill',
                'type': 'ir.actions.act_window',
                'views': [(tree_view.id, 'tree')],
                'domain': [('usd_pool_id','!=',False)],
                'target':'current',


            }
    def open_invoice_usd_pool(self):
        self.ensure_one()
        #form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.view_account_invoice_usd_pool_tree')
        for one in self:
            return {
                'name': u'美金池',
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'account.invoice',
                'type': 'ir.actions.act_window',
                'views': [(tree_view.id, 'tree')],
                'domain': [('usd_pool_id','=',one.id)],
                'target':'current',
                # 'flags': {
                #     'tree': {
                #         'options': {
                #             'pager': 'True',
                #         },
                #     }
                # },
            }




