# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp
from lxml import etree
from odoo.exceptions import UserError, ValidationError


class wizard_renling(models.TransientModel):
    _name = 'wizard.renling'

    @api.depends('partner_id')
    def compute_invoice_advance(self):
        if self.renling_type == 'other_payment':
            sale_other_invoice_ids = self.env['account.invoice'].search(
                [('residual', '>', 0), ('state', '=', 'open'), ('invoice_attribute', '=', 'other_payment'),
                 ('yjzy_type_1', '=', 'sale'), ('type', '=', 'out_invoice')])
            self.sale_other_invoice_ids = sale_other_invoice_ids

    @api.depends('partner_id')
    def _compute_customer_advance_payment_ids(self):
        for one in self:
            if self.invoice_ids:
                self.invoice_ids = False
            so = []
            for x in one.invoice_ids:
                for line in x.invoice_line_ids.mapped('so_id'):
                    so.append(line.id)
                so.append(False)  #

            customer_advance_payment_ids = self.env['account.payment'].search(
                [('partner_id', '=', one.partner_id.id), ('sfk_type', '=', 'ysrld'),
                 ('state', 'in', ['posted']), ('advance_balance_total', '!=', 0)])
            customer_advance_payment_ids_count = len(customer_advance_payment_ids)
            one.customer_advance_payment_ids_count = customer_advance_payment_ids_count
            one.customer_advance_payment_ids = customer_advance_payment_ids
            if customer_advance_payment_ids_count == 0:
                one.ysrld_ok = False
            else:
                one.ysrld_ok = True

            print('one.customer_advance_payment_ids', one.customer_advance_payment_ids)

    def _default_line_ids(self):  # 参考one2many的default 默认核心参考
        res = []
        product = self.env['product.product'].search([('name', '=', '营业外收入')], limit=1)
        account = product.property_account_income_id
        res.append((0, 0, {
            # 'name': '%s:%s' % (product.name, self.name),
            'product_id': product.id,
            'quantity': 1,
            'account_id': account.id, }))
        return res or None

    # @api.onchange('invoice_ids')
    # def _onchange_customer_advance_payment_ids(self):
    #     self._compute_customer_advance_payment_ids()

    # def _default_ysrld_ok(self):
    #     if self.customer_advance_payment_ids_count == 0:
    #         return False
    #     else:
    #         return True
    # @api.onchange('partner_id')
    # def onchange_partner_id(self):

    # 1223 其他应收
    name_title = fields.Char(u'账单描述')
    invoice_partner = fields.Char(u'账单对象')
    line_ids = fields.One2many('wizard.invoice.line', 'renling_id', u'其他应收明细',
                               default=lambda self: self._default_line_ids())

    other_invoice_amount = fields.Monetary('金额', currency_field='currency_id')
    # 1115
    customer_advance_payment_ids = fields.Many2many('account.payment', u'相关预收',
                                                    compute=_compute_customer_advance_payment_ids
                                                    )  #
    customer_advance_payment_ids_count = fields.Integer('相关预收数量', compute=_compute_customer_advance_payment_ids)  #
    ysrld_ok = fields.Boolean('是否预收-应收认领', default=False, compute=_compute_customer_advance_payment_ids, store=True)

    partner_id = fields.Many2one('res.partner', u'合作伙伴',
                                 domain=[('is_company', '=', True), ('parent_id', '=', False), ('customer', '=', 1),
                                         ('name', 'not in', ['未定义', '国税局']), ('invoice_open_ids_count', '!=', 0)])

    partner_advance_id = fields.Many2one('res.partner', u'合作伙伴',
                                         domain=[('is_company', '=', True), ('parent_id', '=', False),
                                                 ('customer', '=', 1),
                                                 ('name', 'not in', ['未定义', '国税局'])])

    yjzy_payment_id = fields.Many2one('account.payment', u'日常收款单')
    yjzy_payment_amount = fields.Monetary(u'收款单原始金额',currency_field='currency_id',related='yjzy_payment_id.amount')
    yjzy_payment_balance = fields.Monetary(u'收款单剩余金额', currency_field='currency_id',related='yjzy_payment_id.balance')
    gongsi_id = fields.Many2one('gongsi', '内部公司')

    invoice_ids = fields.Many2many('account.invoice', 'ref_wz_inv', 'inv_id', 'wz_id', u'Invoice')
    so_id = fields.Many2one('sale.order', '销售合同')
    so_id_currency_id = fields.Many2one('res.currency', related='so_id.currency_id')
    amount_total_so = fields.Monetary('合同金额', related='so_id.amount_total', currency_field='so_id_currency_id')

    customer_payment_term_id = fields.Many2one('account.payment.term', u'客户付款条款',
                                               related='partner_id.property_payment_term_id')
    sale_payment_term_id = fields.Many2one('account.payment.term', u'销售单付款条款', related='so_id.payment_term_id')
    so_pre_advance = fields.Monetary(u'应收预收款', currency_field='so_id_currency_id', related='so_id.pre_advance')
    so_real_advance = fields.Monetary(u'预收金额', currency_field='so_id_currency_id', related='so_id.real_advance')

    btd_id = fields.Many2one('back.tax.declaration', '退税申报单')
    sale_other_invoice_ids = fields.Many2many('account.invoice', 'p3_id', 'i3_id', '未完成认领其他应收',
                                              compute='compute_invoice_advance')

    currency_id = fields.Many2one('res.currency', '货币', related='yjzy_payment_id.currency_id')

    ysrld_amount = fields.Monetary('预收认领金额', currency_field='currency_id')
    step = fields.Selection([('10', '10'), ('20', '20')], '步骤', default='10')

    renling_type = fields.Selection([('yshxd', '应收认领'),
                                     ('ysrld', '预收认领'),
                                     ('back_tax', '退税认领'), ('other_payment', '其他认领')], u'认领属性')

    declaration_date = fields.Date('申报日期')
    company_currency_id = fields.Many2one('res.currency', string='公司货币',
                                          default=lambda self: self.env.user.company_id.currency_id.id,
                                          readonly=True)
    declaration_amount_all = fields.Monetary(u'本次申报金额', currency_field='company_currency_id',
                                             related='btd_id.declaration_amount_all')
    btd_line_ids = fields.Many2many('back.tax.declaration.line', 'ref_btd_id', 'wz_renling_id', u'申报明细')
    other_payment_invoice_ok = fields.Boolean('待认领其他应收', default=True)
    other_payment_invoice_ok_f = fields.Boolean('是否其他应付', default=False)

    @api.onchange('other_invoice_amount')
    def onchange_other_invoice_amount(self):
        other_invoice_amount = self.other_invoice_amount
        self.line_ids[0].price_unit = other_invoice_amount

    @api.onchange('partner_advance_id')
    def onchange_partner_advance_id(self):
        self.partner_id = self.partner_advance_id

    @api.onchange('btd_id')
    def onchange_btd_id(self):
        # invoice_ids = self.invoice_ids
        btd_line_ids = self.btd_line_ids
        # for line in self.btd_id.btd_line_ids.mapped('invoice_id') - self.invoice_ids:
        #     invoice_ids += line
        #     print('line_1111111111', line)
        for line in self.btd_id.btd_line_ids - self.btd_line_ids:
            btd_line_ids += line
        self.btd_line_ids = btd_line_ids
        # self.invoice_ids = btd_line_ids.mapped('invoice_id')
        # self.btd_id = False
        self.step = '20'

    @api.onchange('renling_type')
    def onchange_renling_type(self):
        renling_type = self.renling_type
        if renling_type in ['yshxd', 'ysrld']:
            partner_id = False
            self.partner_advance_id = False
            self.step = '10'
            self.btd_id = False
            self.other_payment_invoice_ok_f = False
        elif renling_type == 'back_tax':
            partner_id = self.env.ref('yjzy_extend.partner_back_tax')
            self.step = '10'
            self.btd_id = False
            self.other_payment_invoice_ok_f = False
        elif renling_type == 'other_payment':
            partner_id = self.env['res.partner'].search([('name', '=', '未定义'), ('customer', '=', True)])
            self.step = '20'
            self.btd_id = False
            self.other_payment_invoice_ok_f = True

        else:
            partner_id = False
            self.step = '10'
        self.btd_id = False
        self.btd_line_ids = False
        self.partner_id = partner_id
        self.invoice_ids = False
        self.other_payment_invoice_ok = True

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        renling_type = self.renling_type
        if renling_type in ['yshxd', 'ysrld'] and self.partner_id:
            self.step = '20'

    def open_ysrld(self):
        tree_view = self.env.ref('yjzy_extend.view_ysrld_reconcile_tree_1')
        form_view = self.env.ref('yjzy_extend.view_ysrld_form')
        return {
            'name': '预收认领单',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('id', 'in', [x.id for x in self.customer_advance_payment_ids])],
            'target': 'current',
            'type': 'ir.actions.act_window',
            'context': {'show_shoukuan': True,
                        'default_sfk_type': 'ysrld',
                        'default_payment_type': 'inbound',
                        'default_be_renling': True,
                        'default_advance_ok': True,
                        'default_partner_type': 'customer',
                        }
        }

    def apply(self):
        self.ensure_one()

        self.create_yshxd_ysrl()

    # 从预收单申请应收
    def create_ysrld_yxhxd(self):
        # if len(self.invoice_ids.mapped('currency_id')) > 1:
        #     raise Warning('不同币种的账单，不能同时认领！')
        sfk_type = 'yshxd'
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        yshxd_obj = self.env['account.reconcile.order']
        yshxd_id = yshxd_obj.with_context({'default_invoice_ids': self.invoice_ids}).create({
            'name': name,
            'operation_wizard': '25',
            'yjzy_advance_payment_id': self.yjzy_payment_id.id,
            'partner_id': self.partner_id.id,
            'sfk_type': sfk_type,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'be_renling': True,
            'invoice_attribute': 'normal',
            'yjzy_type': 'sale',
            'hxd_type_new': '10'

        })
        # self.make_lines_so(yshxd_id)
        # yshxd_id.compute_advice_amount_advance_org()
        form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_new').id
        return {
            'name': '认领单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.reconcile.order',
            'views': [(form_view, 'form')],
            'res_id': yshxd_id.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': {'default_sfk_type': 'yshxd',
                        'active_id': yshxd_id.id,
                        'open': 1
                        }
        }

    def create_yshxd_ysrl(self):
        invoice_ids = self.invoice_ids
        hxd_line_approval_ids = self.env['account.reconcile.order.line'].search(
            [('invoice_id.id', 'in', invoice_ids.ids), ('order_id.state', 'not in', ['done', 'approved'])])
        order_id = hxd_line_approval_ids.mapped('order_id')
        if hxd_line_approval_ids:
            view = self.env.ref('sh_message.sh_message_wizard_1')
            view_id = view and view.id or False
            context = dict(self._context or {})
            context['message'] = "选择的应收账单，有存在审批中的预收认领，请查验"
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
        for one in self.invoice_ids:
            if one.currency_id != self.currency_id:
                raise Warning('选择的账单和收款单币种不一致！')
        if len(self.invoice_ids.mapped('currency_id')) > 1:
            raise Warning('不同币种的账单，不能同时认领！')

        if not self.renling_type:
            raise Warning('未选择认领属性')
        if self.renling_type == 'yshxd':
            if not self.partner_id:
                raise Warning('请先选择客户')
            if not self.invoice_ids:
                raise Warning('请先选择需要认领的账单')
            if len(self.invoice_ids) > 1:
                raise Warning('一次只允许认领一张！')
        if self.renling_type == 'ysrld':
            if not self.partner_id:
                raise Warning('请先选择客户')
        if self.renling_type == 'other_payment':
            if not self.partner_id:
                raise Warning('请先选择客户')
            if not self.invoice_ids and self.other_payment_invoice_ok:
                raise Warning('请先选择需要认领的账单')
            if len(self.invoice_ids) > 1:
                raise Warning('一次只允许认领一张！')
        elif self.renling_type in ['back_tax']:
            if not self.partner_id:
                raise Warning('请先选择客户')
            if not self.btd_line_ids:
                raise Warning('请先选择需要认领的退税申报')
        back_tax_declaration_id = False
        name_title = ''
        invoice_partner = ''
        if self.renling_type in ['yshxd']:
            invoice_attribute = 'normal'
            sfk_type = 'yshxd'
            yjzy_type = 'sale'
            hxd_type_new = '20'  # 默认是收款认领，当点应收认领的时候状态进行判断
            operation_wizard = '10'
            print('operation_wizard_akiny',operation_wizard)
            # hxd_type_new = '20'  #单独认领收款-应收
        elif self.renling_type == 'back_tax':
            invoice_attribute = 'normal'
            operation_wizard = '10'
            sfk_type = 'yshxd'
            yjzy_type = 'back_tax'
            back_tax_declaration_id = self.btd_id.id
            hxd_type_new = '20'
        elif self.renling_type == 'other_payment':
            invoice_attribute = 'other_payment'
            sfk_type = 'yshxd'
            yjzy_type = 'other_payment_sale'
            hxd_type_new = '20'
            operation_wizard = '10'
            invoice_partner = self.invoice_ids[0].invoice_partner
            name_title = self.invoice_ids[0].name_title
        else:
            invoice_attribute = False
            operation_wizard = '10'
            sfk_type = 'ysrld'

        yshxd_obj = self.env['account.reconcile.order']
        ysrld_obj = self.env['account.payment']
        if self.renling_type == 'back_tax':
            invoice_ids = self.btd_line_ids.mapped('invoice_id')
        else:
            invoice_ids = self.invoice_ids
        print('invoice_ids', invoice_ids)

        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        if self.renling_type in ['yshxd', 'back_tax', 'other_payment']:

            yshxd_id = yshxd_obj.with_context({'default_invoice_ids': invoice_ids,'default_sfk_type': 'yshxd'}).create({
                'name': name,
                'invoice_partner':invoice_partner,
                'name_title':name_title,
                'operation_wizard': operation_wizard,
                'partner_id': self.partner_id.id,
                'sfk_type': 'yshxd',
                'renling_type': self.renling_type,
                'back_tax_declaration_id': back_tax_declaration_id,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'yjzy_payment_id': self.yjzy_payment_id.id,
                'be_renling': True,
                'invoice_attribute': invoice_attribute,
                'yjzy_type': yjzy_type,
                'hxd_type_new': hxd_type_new

            })
            if self.renling_type != 'yshxd':
                yshxd_id.with_context({'ysrld_amount':self.ysrld_amount}).make_line_no()
                yshxd_id.operation_wizard = '10'
                stage_id = yshxd_id._stage_find(domain=[('code', '=', '035')])
                print('_stage_find', stage_id)
                yshxd_id.write({'stage_id': stage_id.id,
                                'state': 'draft',
                                # 'operation_wizard':'25'
                                })
            else:

                yshxd_id.with_context({'ysrld_amount':self.ysrld_amount}).make_line_no()
                yshxd_id.make_account_payment_state_ids()
                # if yshxd_id.supplier_advance_payment_ids_count != 0:
                #     yshxd_id.operation_wizard = '30'
                # else:
                #     yshxd_id.operation_wizard = '10'
                #     yshxd_id.hxd_type_new = '20'
                stage_id = yshxd_id._stage_find(domain=[('code', '=', '017')])
                print('_stage_find', stage_id)
                yshxd_id.write({'stage_id': stage_id.id,
                                'state': 'posted',
                                # 'operation_wizard':'25'
                                })
            form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_new').id
            return {
                'name': '应收认领单',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.reconcile.order',
                'views': [(form_view, 'form')],
                'res_id': yshxd_id.id,
                'target': 'current',
                'type': 'ir.actions.act_window',
                'context': {'default_sfk_type': 'yshxd',
                            'active_id': yshxd_id.id,
                            'bank_amount': 1,
                            'show_so': 1,
                            'open': 1,
                            'advance_so_amount': 1,
                            'only_number': 1,
                            }

            }
        elif self.renling_type in ['ysrld']:
            journal_domain = [('code', '=', 'ysdrl'), ('company_id', '=', self.env.user.company_id.id)]
            journal_id = self.env['account.journal'].search(journal_domain, limit=1)
            ysrld_amount = self.ysrld_amount
            ysrld = ysrld_obj.with_context({'bank_amount': 1, 'show_shoukuan': True, 'default_sfk_type': 'ysrld',
                                            'default_payment_type': 'inbound', 'default_be_renling': True,
                                            'default_advance_ok': True, 'default_partner_type': 'customer', }).create({
                'name': name,
                'advance_ok': True,
                'partner_id': self.partner_id.id,
                'sfk_type': sfk_type,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'yjzy_payment_id': self.yjzy_payment_id.id,
                'be_renling': True,
                'invoice_attribute': invoice_attribute,
                'currency_id': self.currency_id.id,
                'payment_method_id': 2,
                'amount': ysrld_amount,
                'journal_id': journal_id.id,
                'so_id': self.so_id.id,

            })
            form_view = self.env.ref('yjzy_extend.view_ysrld_form_latest').id
            return {
                'name': '预收认领单',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.payment',
                'views': [(form_view, 'form')],
                'res_id': ysrld.id,
                'target': 'current',
                'type': 'ir.actions.act_window',
                'context': {'default_sfk_type': 'ysrld',
                            'active_id': ysrld.id,
                            'bank_amount': 1,
                            'show_so': 1,
                            # 'ysrls_open':1
                            }

            }

    def _prepare_sale_invoice_line(self, inv):
        self.ensure_one()
        dic_so_invl = {}
        for line in inv.invoice_line_ids:
            if line.sale_line_ids:
                so = line.sale_line_ids[0].order_id
                if so in dic_so_invl:
                    dic_so_invl[so] |= line
                else:
                    dic_so_invl[so] = line
        return dic_so_invl or False

    # def make_lines_so(self, yshxd_id):
    #     self.ensure_one()
    #     ctx = self.env.context
    #     order_id = yshxd_id  # ctx.get('active_id')
    #     print('order_id', order_id)
    #     line_obj = self.env['account.reconcile.order.line']
    #     line_no_obj = self.env['account.reconcile.order.line.no']
    #
    #     order_id.line_ids = None
    #     # if self.no_sopo:
    #     #     for invoice in self.invoice_ids:
    #     #         line_obj.create({
    #     #             'order_id': self.id,
    #     #             'invoice_id': invoice.id,
    #     #             'amount_invoice_so': invoice.amount_total,
    #     #         })
    #     # else:
    #     line_ids = line_obj.browse([])
    #     line_id = None
    #     #如果是退税，就取退税申报明细的对应的发票
    #     if self.renling_type == 'back_tax':
    #         invoice_ids = self.btd_line_ids.mapped('invoice_id')
    #     else:
    #         invoice_ids = self.invoice_ids
    #     print('invoice_ids',invoice_ids)
    #     declaration_amount = 0
    #     if self.renling_type == 'back_tax':
    #         for btd in self.btd_line_ids:
    #             so_invlines = self._prepare_sale_invoice_line(btd.invoice_id)
    #             if btd.invoice_id.yjzy_type == 'back_tax' or btd.invoice_id.yjzy_type_1 == 'back_tax':
    #                 declaration_amount = btd.declaration_amount
    #             else:
    #                 declaration_amount = 0
    #             print('declaration_amount_0000000000', declaration_amount)
    #             if not so_invlines:
    #                 line_id = line_obj.create({
    #                     'order_id': order_id.id,
    #                     'invoice_id': btd.invoice_id.id,
    #                     'amount_invoice_so': btd.invoice_id.amount_total,
    #                     'amount_payment_org': declaration_amount
    #                 })
    #             line_ids |= line_id
    #     else:
    #         for invoice in invoice_ids:
    #             so_invlines = self._prepare_sale_invoice_line(invoice)
    #             if not so_invlines:
    #                 line_id = line_obj.create({
    #                     'order_id': order_id.id,
    #                     'invoice_id': invoice.id,
    #                     'amount_invoice_so': invoice.amount_total,
    #                     'amount_payment_org': 0
    #                 })
    #             else:
    #                 for so, invlines in so_invlines.items():
    #                     line_id = line_obj.create({
    #                         'order_id': order_id.id,
    #                         'so_id': so.id,
    #                         'invoice_id': invoice.id,
    #                         'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
    #                         'amount_payment_org': 0,
    #
    #                     })
    #             line_ids |= line_id
    #     order_id.invoice_ids = invoice_ids
    #     # self.order_id.invoice_attribute = self.invoice_ids[0].invoice_attribute
    #     self.invoice_partner = invoice_ids[0].invoice_partner
    #     self.name_title = invoice_ids[0].name_title
    #     so_po_dic = {}
    #     print('line_obj', line_ids)
    #     order_id.line_no_ids = None
    #     # yjzy_advance_payment_id = self.yjzy_advance_payment_id
    #     for i in line_ids:
    #         invoice = i.invoice_id
    #         amount_invoice_so = i.amount_invoice_so
    #         advance_residual2 = i.advance_residual2
    #         amount_payment_org = i.amount_payment_org
    #
    #         order = i.order_id
    #
    #         k = invoice.id
    #
    #         if i.invoice_id.yjzy_type == 'back_tax' or i.invoice_id.yjzy_type_1 == 'back_tax':
    #             declaration_amount_1 = amount_payment_org
    #         else:
    #             declaration_amount_1 = 0
    #         if k in so_po_dic:
    #             print('k', k)
    #             so_po_dic[k]['amount_invoice_so'] += amount_invoice_so
    #             so_po_dic[k]['advance_residual2'] += advance_residual2
    #             so_po_dic[k]['amount_payment_org'] += declaration_amount_1
    #         else:
    #             print('k1', k)
    #             so_po_dic[k] = {
    #                 'invoice_id': invoice.id,
    #                 'amount_invoice_so': amount_invoice_so,
    #                 'advance_residual2': advance_residual2,
    #                 # 'yjzy_payment_id': yjzy_advance_payment_id.id
    #                 'amount_payment_org': declaration_amount_1,
    #             }
    #
    #     for kk, data in list(so_po_dic.items()):
    #         line_no = line_no_obj.create({
    #             'order_id': order_id.id,
    #             'invoice_id': data['invoice_id'],
    #             'amount_invoice_so': data['amount_invoice_so'],
    #             'advance_residual2': data['advance_residual2'],
    #             # 'yjzy_payment_id': yjzy_advance_payment_id.id,
    #             'amount_payment_org': data['amount_payment_org'],
    #         })
    #
    # # def apply(self):
    # #     self.ensure_one()
    # #     ctx = self.env.context
    # #     bill_id = ctx.get('active_id')
    # #     tb = self.env['transport.bill'].browse(bill_id)
    # #     sale_orders = self.so_ids
    # #
    # #     if len(sale_orders.mapped('partner_id')) > 1:
    # #         raise Warning(u'必须是同一个客户的订单')
    # #
    # #     bill_line_obj = self.env['transport.bill.line']
    # #     for sol in sale_orders.mapped('order_line'):
    # #         if sol.qty_undelivered > 0:
    # #             so = sol.order_id
    # #             #so.tb_ids |= tb
    # #             bill_line_obj.create({
    # #                 'bill_id': bill_id,
    # #                 'sol_id': sol.id,
    # #                 'qty': sol.qty_undelivered,
    # #                 'qty1stage': sol.qty_unreceived,
    # #                 'back_tax': sol.product_id.back_tax,
    # #             })
    # #     return True

    def create_tb_po_invoice(self):
        form_view = self.env.ref('yjzy_extend.tb_po_form')
        type = self.renling_type
        yjzy_type_1 = self.env.context.get('default_yjzy_type_1')
        type_invoice = self.env.context.get('default_type_invoice')
        print('type_invoice', type_invoice, yjzy_type_1)
        tb_po_invoice_obj = self.env['tb.po.invoice']
        tb_po_invoice_id = tb_po_invoice_obj.create({'currency_id': self.currency_id.id,
                                                     'manual_currency_id': self.currency_id.id,
                                                     'type': type,
                                                     'yjzy_type_1': yjzy_type_1,
                                                     'type_invoice': type_invoice,
                                                     'yjzy_payment_id': self.yjzy_payment_id.id,
                                                     })
        print('tb_po_invoice_id', tb_po_invoice_id)
        return {
            'name': '其他应收申请单',
            'view_type': 'tree,form',
            "view_mode": 'form',
            'res_model': 'tb.po.invoice',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': tb_po_invoice_id.id,
            'target': 'current',
            # 'domain': [('yjzy_advance_payment_id', '=', self.id)],
            'context': {}
        }

    def create_tb_po_invoice_new(self):
        form_view = self.env.ref('yjzy_extend.tb_po_other_form')
        type = self.renling_type
        yjzy_type_1 = self.env.context.get('default_yjzy_type_1')
        type_invoice = self.env.context.get('default_type_invoice')
        tb_po_invoice_line = self.env['extra.invoice.line']
        print('type_invoice', type_invoice, yjzy_type_1)

        tb_po_invoice_obj = self.env['tb.po.invoice']
        tb_po_invoice_id = tb_po_invoice_obj.with_context(
            {'default_type': 'other_payment', 'default_yjzy_type_1': 'other_payment_sale', 'not_is_default': 1,
             'default_type_invoice': 'out_invoice'}).create({'currency_id': self.currency_id.id,
                                                             'manual_currency_id': self.currency_id.id,
                                                             'type': type,
                                                             'yjzy_type_1': yjzy_type_1,
                                                             'type_invoice': type_invoice,
                                                             'yjzy_payment_id': self.yjzy_payment_id.id,
                                                             'name_title': self.name_title,
                                                             'invoice_partner': self.invoice_partner,
                                                             'other_invoice_amount': self.other_invoice_amount,

                                                             })
        for one in self.line_ids:
            product = one.product_id
            quantity = one.quantity
            price_unit = one.price_unit
            account = one.account_id
            # if product:
            #     account = product.product_tmpl_id._get_product_accounts()['expense']
            #     if not account:
            #         raise UserError(
            #             _(
            #                 "No Expense account found for the product %s (or for its category), please configure one.") % (
            #                 self.product_id.name))
            # else:
            #     account = self.env['ir.property'].with_context(force_company=self.company_id.id).get(
            #         'property_account_expense_categ_id', 'product.category')
            #     if not account:
            #         raise UserError(
            #             _(
            #                 'Please configure Default Expense account for Product expense: `property_account_expense_categ_id`.'))
            tb_po_invoice_line = tb_po_invoice_line.create({
                'tb_po_id': tb_po_invoice_id.id,
                'name': '%s' % (product.name),
                'product_id': product.id,
                'quantity': quantity,
                'price_unit': price_unit,
                'account_id': account.id
            })
        print('tb_po_invoice_id', tb_po_invoice_id)
        return {
            'name': '其他应收申请单',
            'view_type': 'tree,form',
            "view_mode": 'form',
            'res_model': 'tb.po.invoice',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': tb_po_invoice_id.id,
            'target': 'current',
            # 'domain': [('yjzy_advance_payment_id', '=', self.id)],
            'context': {'not_is_default': 1}
        }


class Wizard_Invoice_Line(models.TransientModel):
    _name = 'wizard.invoice.line'
    _description = "wizard Invoice Line"

    @api.one
    @api.depends('price_unit', 'quantity', 'product_id', )
    def _compute_price(self):
        price = self.price_unit
        self.price_total = self.quantity * price

    # def _default_account(self):
    #     if self._context.get('journal_id'):
    #         journal = self.env['account.journal'].browse(self._context.get('journal_id'))
    #         if self._context.get('type_invoice') in ('out_invoice', 'in_refund'):
    #             return journal.default_credit_account_id.id
    #         return journal.default_debit_account_id.id

    renling_id = fields.Many2one('wizard.renling', u'认领单')
    product_id = fields.Many2one('product.product', string='Product',
                                 ondelete='restrict', index=True)
    currency_id = fields.Many2one('res.currency', related='renling_id.currency_id')
    price_unit = fields.Float(string='Unit Price', required=True, digits=(2, 2), )
    price_total = fields.Monetary(string='Amount', currency_field='currency_id',
                                  store=True, readonly=True, compute='_compute_price',
                                  help="Total amount with taxes")
    quantity = fields.Float(string='Quantity', digits=(2, 2),
                            required=True, default=1)

    account_id = fields.Many2one('account.account', string='Account',

                                 help="The income or expense account related to the selected product.")

#####################################################################################################################
