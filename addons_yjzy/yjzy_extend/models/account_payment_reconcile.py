# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.addons.account.models.account_payment import account_payment as Account_Payment
from .comm import sfk_type

Option_Add = [
    ('advance', u'预收付'),
    ('date_after_ship', u'客户交单后的天数'),
    ('date_after_finish', u'供应商交单日期'),
]




class account_payment(models.Model):
    _inherit = 'account.payment'

    def compute_advance_balance_aml_total(self):
        for one in self:
            advance_balance_aml_total = 0
            all_lines = one.aml_advace_ids
            if one.sfk_type == 'ysrld':
                lines = all_lines.filtered(lambda x: x.account_id.code == '2203')
                if one.currency_id.name == 'CNY':
                    advance_balance_aml_total = sum([x.credit - x.debit for x in lines])
                else:
                    advance_balance_aml_total = sum([-1 * x.amount_currency for x in lines])
            if one.sfk_type == 'yfsqd':
                lines = all_lines.filtered(lambda x: x.account_id.code == '1123')
                if one.currency_id.name == 'CNY':
                    advance_balance_aml_total = sum([-1 * (x.credit - x.debit) for x in lines])
                else:
                    advance_balance_aml_total = sum([1 * x.amount_currency for x in lines])

            one.advance_balance_aml_total = advance_balance_aml_total
            # if advance_balance_aml_total == 0 and one.state_1 == '50_posted':
            #     one.state_1 = '60_done'
            #     one.test_reconcile()
            #     one.write({'state': 'reconciled'})
    def compute_payment_ids_count(self):
        for one in self:
            payment_ids_count= len(one.payment_ids)
            one.payment_ids_count = payment_ids_count


    @api.depends('yjzy_payment_id','invoice_log_id')
    def compute_invoice_id(self):
        for one in self:
            yjzy_payment_id = one.yjzy_payment_id
            invoice_log_id = one.invoice_log_id
            if not yjzy_payment_id and not invoice_log_id:
                payment_log_ids = None
            elif yjzy_payment_id:
                payment_log_ids = yjzy_payment_id.payment_ids

            else:
                payment_log_ids = invoice_log_id.payment_log_ids
            if payment_log_ids:
                payment_log_no_done_ids = payment_log_ids.filtered(lambda x: x.state not in ['posted', 'reconciled'])
            else:
                payment_log_no_done_ids = None
            one.payment_log_ids = payment_log_ids
            one.payment_log_no_done_ids = payment_log_no_done_ids

    @api.depends('yjzy_payment_id','invoice_log_id')
    def compute_move_line_com_ids(self):
        for one in self:
            yjzy_payment_id = one.yjzy_payment_id
            invoice_log_id = one.invoice_log_id
            move_line_com_dic = []
            if not yjzy_payment_id and not invoice_log_id:
                move_line_com_ids = False
            elif yjzy_payment_id and not invoice_log_id:
                if yjzy_payment_id.sfk_type == 'yfsqd':
                    move_line_com_ids = yjzy_payment_id.aml_com_yfzk_ids
                else:
                    move_line_com_ids = yjzy_payment_id.aml_com_yszk_ids
            else:
                if invoice_log_id.type == 'out_invoice':
                    move_line_com_ids = invoice_log_id.move_line_com_yszk_ids

                else:
                    move_line_com_ids = invoice_log_id.move_line_com_yfzk_ids
            reconcile_order_ids = invoice_log_id.reconcile_order_ids
            advance_reconcile_order_yjzy_line_ids = yjzy_payment_id.advance_reconcile_order_line_ids

            # for x in move_line_com_ids:  # 参考M2M的自动多选
            #     move_line_com_dic.append(x.id)
            # print('move_line_com_dic_akiny',move_line_com_dic,move_line_com_ids)
            # one.move_line_com_ids = move_line_com_dic
            # one.write({'move_line_com_ids':[(6,0,[x.id for x in move_line_com_ids])]})
            one.move_line_com_ids = move_line_com_ids
            one.reconcile_order_ids = reconcile_order_ids
            one.advance_reconcile_order_yjzy_line_ids = advance_reconcile_order_yjzy_line_ids
            one.reconcile_order_ids_count = len(reconcile_order_ids)
            one.advance_reconcile_order_yjzy_line_ids_count = len(advance_reconcile_order_yjzy_line_ids)

    @api.depends('yjzy_payment_id')
    def compute_payment_ids_yjzy(self):
        for one in self:
            payment_ids_yjzy = one.yjzy_payment_id.payment_ids.filtered(lambda x: x.sfk_type in ['reconcile_yfsqd','reconcile_ysrld'])
            one.payment_ids_yjzy = payment_ids_yjzy
            one.payment_ids_yjzy_count = len(payment_ids_yjzy)


    payment_log_ids = fields.Many2many('account.payment', compute=compute_invoice_id)
    payment_log_no_done_ids = fields.Many2many('account.payment', compute=compute_invoice_id)

    move_line_com_ids = fields.Many2many('account.move.line.com',compute=compute_move_line_com_ids)
    reconcile_order_ids = fields.Many2many('account.reconcile.order',compute=compute_move_line_com_ids)
    reconcile_order_ids_count = fields.Integer(u'核销单据数量', compute=compute_move_line_com_ids)
    #被核销的预收预付的认领明细
    advance_reconcile_order_yjzy_line_ids = fields.Many2many('account.reconcile.order.line',compute=compute_move_line_com_ids)
    advance_reconcile_order_yjzy_line_ids_count = fields.Integer(u'预收认领预付申请数量', compute=compute_move_line_com_ids)

    payment_ids_yjzy = fields.Many2many('account.payment','预收预付的核销单',compute=compute_payment_ids_yjzy)
    payment_ids_yjzy_count = fields.Integer(u'预收认领预付核销数量', compute=compute_payment_ids_yjzy)
    payment_ids_count = fields.Integer(u'预收认领预付申请数量', compute=compute_payment_ids_count)



    reconcile_ysrld_ids = fields.One2many('account.payment','yjzy_payment_id',u'预收核销',)#domain=[('sfk_type','=','reconcile_ysrld')]其实就是payment_ids包括了认领和核销的

    reconcile_type_reconcile = fields.Selection([('payment_in',u'收款单核销'),
                                       ('payment_out',u'付款单核销'),
                                       ('advance_payment_in',u'预收款核销'),
                                       ('advance_payment_out',u'预付款单核销'),
                                       ('invoice_customer',u'应收核销'),
                                       ('invoice_supplier',u'应付核销'),],u'核销类型')#付款单核销注意付款申请单和付款指令两个，应该是对付款申请单进行核销

    aml_advace_ids = fields.One2many('account.move.line', 'new_advance_payment_id', u'预收付余额相关分录')
    advance_balance_aml_total = fields.Monetary(u'预收余额', compute=compute_advance_balance_aml_total, currency_field='yjzy_payment_currency_id',)

    yjzy_payment_advance_balance = fields.Monetary(u'未完成认领金额',
                                                   related='yjzy_payment_id.advance_balance_total',
                                                   currency_field='yjzy_payment_currency_id')

    amount_state =fields.Boolean('核销金额是否已确认',default=False)







    #创建核销单
    def create_reconcile(self):
        if self.advance_balance_total <= 0 :
            raise Warning('未认领金额不大于0，不需要核销')
        if len(self.payment_ids.filtered(lambda x: x.state not in ['posted','reconciled'])) > 0:
            raise Warning('存在未完成的核销单，不允许创建核销！')
        form_view = self.env.ref('yjzy_extend.view_ysrld_reconcile_form')
        ctx = {}
        partner = self.partner_id
        if self.sfk_type == 'ysrld':
            # partner = self.env['res.partner'].search([('name', '=', u'未定义')], limit=1)
            so_id = self.so_id

            advance_account_id = self.env['account.account'].search([('code','=','5609'),('company_id', '=', self.env.user.company_id.id)])
            ctx = { 'show_shoukuan': True,
                    'default_sfk_type': 'reconcile_ysrld',
                    'default_payment_type': 'inbound',
                    'default_be_renling': True,
                    'default_advance_ok': True,
                    'default_partner_type': 'customer',
                    'default_partner_id':partner.id,
                    'default_yjzy_payment_id':self.id,
                    'default_advance_account_id':advance_account_id.id,
                    'default_reconcile_type': '50_reconcile',

                    'default_so_id':so_id.id}
        if self.sfk_type == 'yfsqd':
            # partner = self.env['res.partner'].search([('name', '=', u'未定义')], limit=1)
            po_id = self.po_id
            advance_account_id = self.env['account.account'].search(
                [('code', '=', '5609'), ('company_id', '=', self.env.user.company_id.id)])
            ctx = {'show_shoukuan': True,
                   'default_sfk_type': 'reconcile_yfsqd',
                   'default_payment_type': 'outbound',
                   'default_be_renling': True,
                   'default_advance_ok': True,
                   'default_partner_type': 'supplier',
                   'default_partner_id': partner.id,
                   'default_yjzy_payment_id': self.id,
                   'default_advance_account_id': advance_account_id.id,
                   'default_reconcile_type': '50_reconcile',
                   'default_po_id': po_id.id}
        return {
            'name':u'核销单',
            'view_type':'form',
            'view_mode':'form',
            'type':'ir.actions.act_window',
            'res_model':'account.payment',
            'views':[(form_view.id,'form')],
            'target':'current',
            'context':ctx
        }

    def open_yfsqd(self):
        if self.yjzy_payment_id.sfk_type == 'yfsqd':
            form_view = self.env.ref('yjzy_extend.view_yfsqd_form_open')
            name = '预付申请单'
        else:
            form_view = self.env.ref('yjzy_extend.view_ysrld_form_hx_open')
            name = '预收认领单'
        return {'name': name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.payment',
                'views': [(form_view.id, 'form')],
                'res_id': self.yjzy_payment_id.id,
                'target': 'new',
                'context': {}}

    def open_invoice_id(self):
        form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form_in_one_open').id
        return {'name': '账单查看',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.invoice',
                'views': [(form_view, 'form')],
                'res_id': self.invoice_log_id.id,
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'open': 1}
                }

    def action_confirm_amount(self):
        if self.sfk_type in ['reconcile_yingshou','reconcile_yingfu']:
            self.amount = self.amount_invoice_log
            self.currency_id = self.invoice_log_currency_id
            self.amount_state = True
        else:
            self.write({'amount':self.yjzy_payment_advance_balance,
                        'currency_id':self.yjzy_payment_currency_id.id})
            self.amount_state = True
            # self.amount = self.yjzy_payment_advance_balance
            # self.currency_id = self.yjzy_payment_currency_id
    def action_reconcile_submit(self):
        if self.yjzy_payment_id and (self.so_id or self.po_id) and self.amount != self.yjzy_payment_advance_balance:
            raise Warning('核销金额不等于剩余金额')
        if self.invoice_log_id and self.amount != self.amount_invoice_log:
            raise Warning('核销金额不等于剩余金额')

        self.state_1 = '20_account_submit'

    def action_reconcile_account(self):
        self.state_1 = '30_manager_approve'

    def action_reconcile_manager(self):
        self.post()
        self.state_1 = '60_done'
        if self.yjzy_payment_id:
            self.yjzy_payment_id.compute_advance_balance_total()





