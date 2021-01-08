# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from addons_yjzy.yjzy_extend.models.comm import sfk_type

class wizard_reconcile_invoice(models.TransientModel):
    _name = 'wizard.reconcile.invoice'


    partner_id = fields.Many2one('res.partner', u'合作伙伴', domain=[('customer', '=', True)])
    gongsi_id = fields.Many2one('gongsi', '内部公司')
    purchase_gongsi_id = fields.Many2one('gongsi', '内部采购公司')
    invoice_ids = fields.Many2many('account.invoice', 'ref_rec_inv', 'inv_id', 'tb_id', u'Invoice')
    invoice_po_so_ids = fields.Many2many('account.invoice', 'ref_rec_inv_po_so', 'inv_po_so_id', 'tb_po_so_id', u'Invoice')
    order_id = fields.Many2one('account.reconcile.order',u'核销单')
    type = fields.Selection([('in_invoice','采购发票'),
                             ('out_invoice','采购发票')])
    yjzy_advance_payment_id = fields.Many2one('account.payment',u'预收认领单')
    btd_id = fields.Many2one('back.tax.declaration','退税申报单')
    yjzy_type = fields.Selection([('sale', '销售'),
                                  ('purchase', '采购'),
                                  ('back_tax', '退税')], u'发票类型')
    yjzy_advance_payment_id_sfk_type = fields.Selection(sfk_type, u'收付类型')


    # @api.onchange('btd_id')
    # def onchange_btd_id(self):
    #     if not self.btd_id:
    #         return {}
    #     invoice_ids = self.invoice_ids
    #     for line in self.btd_id.btd_line_ids.mapped('invoice_id') - self.invoice_ids:
    #         invoice_ids += line
    #         print('line_1111111111',line)
    #     self.invoice_ids = invoice_ids
    #     self.btd_id = False
    #     return {}




    def apply(self):
        self.ensure_one()
        ctx = self.env.context
        sfk_type = ctx.get('sfk_type')
        print('ctx', ctx)
        if len(self.invoice_ids) > 1:
            raise Warning('不允许多张账单一起认领！')
        if len(self.invoice_ids.mapped('currency_id')) > 1:
            raise Warning('选择的发票的交易货币不一致，无法同时认领！')
        invoice_id = self.invoice_ids[0]
        self.order_id.invoice_ids = self.invoice_ids
        self.order_id.line_ids.unlink()
        self.order_id.account_payment_state_ids.unlink()
        self.order_id.make_account_payment_state_ids_from_advance(self.yjzy_advance_payment_id)
        # self.order_id.make_lines()
        self.order_id.write({
            'invoice_attribute':invoice_id.invoice_attribute,
            'yjzy_type':invoice_id.yjzy_type_1,

        })




    def create_yfhxd_new(self):
        invoice_ids = self.invoice_ids
        state_draft = len(invoice_ids.filtered(lambda x: x.state != 'open'))
        if len(invoice_ids) > 1:  # attribute == 'other_payment' and
            raise Warning('不允许多张应付一起申请')
        if state_draft >= 1:
            raise Warning('非确认账单不允许创建付款申请')
        if self.yjzy_advance_payment_id_sfk_type in ['yfsqd','yfhxd']:
            po_obj = self.env['purchase.order']
            po_ids = po_obj.browse([])
            for line in invoice_ids:
                for x in line.invoice_line_ids:
                    po_ids |= x.purchase_id
            print('po_ids_akiny',po_ids)
            if self.yjzy_advance_payment_id.po_id and self.yjzy_advance_payment_id.po_id.id not in po_ids.ids:
                raise Warning('预付的采购合同和账单的采购合同不一致！')
            hxd_line_approval_ids = self.env['account.reconcile.order.line.no'].search(
                [('invoice_id.id', 'in', invoice_ids.ids), ('order_id.state', 'not in', ['done', 'approved'])])
            order_id = hxd_line_approval_ids.mapped('order_id')
            if hxd_line_approval_ids:
                view = self.env.ref('sh_message.sh_message_wizard_1')
                view_id = view and view.id or False
                context = dict(self._context or {})
                context['message'] = "选择的应付账单，有存在审批中的，请查验"
                context['res_model'] = "account.reconcile.order"
                context['res_id'] = order_id[0].id
                context['views'] = self.env.ref('yjzy_extend.account_yfhxd_form_view_new').id
                context['no_advance'] = True
                print('context_akiny', context)
                return {
                    'name': 'Success',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sh.message.wizard',
                    'views': [(view_id, 'form')],
                    'target': 'new',
                    'context': context,
                }
            sfk_type = 'yfhxd'
            domain = [('code', '=', 'yfdrl'), ('company_id', '=', self.env.user.company_id.id)]
            name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
            journal = self.env['account.journal'].search(domain, limit=1)
            account_obj = self.env['account.account']
            bank_account = account_obj.search([('code', '=', '10021'), ('company_id', '=', self.env.user.company_id.id)],
                                              limit=1)
            form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new')
            invoice_dic = []
            account_reconcile_order_obj = self.env['account.reconcile.order']
            for one in invoice_ids:
                if one.amount_payment_can_approve_all == 0:
                    raise Warning('可申请付款金额为0，不允许提交！')
                for x in one.yjzy_invoice_wait_payment_ids:  # 参考M2M的自动多选  剩余应付金额！=0的额外账单
                    invoice_dic.append(x.id)
                print('amount_payment_can_approve_all_akiny', one.amount_payment_can_approve_all)
                if one.amount_payment_can_approve_all != 0:  # 考虑已经提交审批的申请
                    invoice_dic.append(one.id)
                print('invoice_dic', invoice_dic)
            account_reconcile_id = account_reconcile_order_obj.with_context({'default_sfk_type': 'yfhxd',}).create({
                'partner_id': invoice_ids[0].partner_id.id,
                'manual_payment_currency_id': invoice_ids[0].currency_id.id,
                'invoice_ids': [(6, 0, invoice_dic)],
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'sfk_type': sfk_type,
                'be_renling': True,
                'name': name,
                'journal_id': journal.id,
                'payment_account_id': bank_account.id,
                'yjzy_type': invoice_ids[0].yjzy_type_1,  # 1207akiny
                'purchase_code_balance': 1,
                'invoice_attribute': invoice_ids[0].invoice_attribute,
                'invoice_type_main': invoice_ids[0].invoice_type_main,
                'invoice_partner': invoice_ids[0].invoice_partner,
                'name_title': invoice_ids[0].name_title,
                'yjzy_advance_payment_id':self.yjzy_advance_payment_id.id,
                'advance_po_amount': 1,
                'show_so': 1,
                'operation_wizard': '20',
                'hxd_type_new': '30'
            })
            account_reconcile_id.write({'sfk_type':sfk_type})
            account_reconcile_id.compute_supplier_advance_payment_ids()
            account_reconcile_id.make_account_payment_state_ids_from_advance(self.yjzy_advance_payment_id)
            print('account_reconcile_id_akiny',account_reconcile_id)
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.reconcile.order',
                'views': [(form_view.id, 'form')],
                'res_id': account_reconcile_id.id,
                'target': 'current',
                'context': {
                            }
            }

        if self.yjzy_advance_payment_id_sfk_type in ['ysrld','yshxd']:
            # so_obj = self.env['sale.order']
            # so_ids = po_obj.browse([])
            # for line in invoice_ids:
            #     for x in line.invoice_line_ids:
            #         po_ids |= x.purchase_id
            # print('po_ids_akiny',po_ids)
            # if self.yjzy_advance_payment_id.po_id and self.yjzy_advance_payment_id.po_id.id not in po_ids.ids:
            #     raise Warning('预付的采购合同和账单的采购合同不一致！')
            hxd_line_approval_ids = self.env['account.reconcile.order.line.no'].search(
                [('invoice_id.id', 'in', invoice_ids.ids), ('order_id.state', 'not in', ['done', 'approved'])])
            order_id = hxd_line_approval_ids.mapped('order_id')
            if hxd_line_approval_ids:
                view = self.env.ref('sh_message.sh_message_wizard_1')
                view_id = view and view.id or False
                context = dict(self._context or {})
                context['message'] = "选择的应收账单，有存在审批中的，请查验"
                context['res_model'] = "account.reconcile.order"
                context['res_id'] = order_id[0].id
                context['views'] = self.env.ref('yjzy_extend.account_yshxd_form_view_new').id
                context['no_advance'] = True
                print('context_akiny', context)
                return {
                    'name': 'Success',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sh.message.wizard',
                    'views': [(view_id, 'form')],
                    'target': 'new',
                    'context': context,
                }

            sfk_type = 'yshxd'
            domain = [('code', '=', 'ysdrl'), ('company_id', '=', self.env.user.company_id.id)]
            name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
            journal = self.env['account.journal'].search(domain, limit=1)
            account_obj = self.env['account.account']
            bank_account = account_obj.search(
                [('code', '=', '10021'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
            form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_new')
            yjzy_payment_id = self.env.context.get('default_yjzy_payment_id')
            invoice_dic = []
            account_reconcile_order_obj = self.env['account.reconcile.order']
            for one in invoice_ids:
                if one.amount_payment_can_approve_all == 0:
                    raise Warning('可申请收款款金额为0，不允许提交！')
                for x in one.yjzy_invoice_wait_payment_ids:  # 参考M2M的自动多选  剩余应付金额！=0的额外账单
                    invoice_dic.append(x.id)
                print('amount_payment_can_approve_all_akiny', one.amount_payment_can_approve_all)
                if one.amount_payment_can_approve_all != 0:  # 考虑已经提交审批的申请
                    invoice_dic.append(one.id)
                print('invoice_dic', invoice_dic)
            account_reconcile_id = account_reconcile_order_obj.with_context({'default_sfk_type': 'yshxd',}).create({
                'partner_id': invoice_ids[0].partner_id.id,
                'manual_payment_currency_id': invoice_ids[0].currency_id.id,
                'invoice_ids': [(6, 0, invoice_dic)],
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'sfk_type': sfk_type,
                'be_renling': True,
                'name': name,
                'journal_id': journal.id,
                'payment_account_id': bank_account.id,
                'yjzy_type': invoice_ids[0].yjzy_type_1,  # 1207akiny
                'purchase_code_balance': 1,
                'invoice_attribute': invoice_ids[0].invoice_attribute,
                'invoice_type_main': invoice_ids[0].invoice_type_main,
                'yjzy_advance_payment_id':self.yjzy_advance_payment_id.id,
                'advance_po_amount': 1,
                'show_so': 1,
                'operation_wizard': '20',
                'hxd_type_new': '10'
            })


            account_reconcile_id.write({'sfk_type':sfk_type})
            account_reconcile_id.compute_supplier_advance_payment_ids()
            account_reconcile_id.make_account_payment_state_ids_from_advance(self.yjzy_advance_payment_id)
            print('account_reconcile_id_akiny',account_reconcile_id)
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.reconcile.order',
                'views': [(form_view.id, 'form')],
                'res_id': account_reconcile_id.id,
                'target': 'current',
                'context': {
                            }
            }


    def create_yfhxd(self):
        invoice_type = self.invoice_ids.mapped('type')
        if len(invoice_type) > 1:
            raise Warning('不同类型的账单不允许一起申请')
        if len(self.invoice_ids) > 1:
            raise Warning('不允许多张账单一起认领！')
        records = self.invoice_ids
        if records and records[0].type in ['in_invoice']:
            records.create_yfhxd_from_multi_invoice(records[0].invoice_attribute)
        if records and records[0].type in ['out_invoice']:
            records.create_yshxd_from_multi_invoice(records[0].invoice_attribute)


#####################################################################################################################
