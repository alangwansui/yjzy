# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning


class wizard_renling(models.TransientModel):
    _name = 'wizard.renling'

    @api.depends('partner_id')
    def compute_invoice_advance(self):
        sale_other_invoice_ids = self.env['account.invoice'].search(
            [('residual', '>', 0), ('state', '=', 'open'), ('invoice_attribute', '=', 'other_payment'),
             ('yjzy_type_1', '=', 'sale'), ('type', '=', 'out_invoice')])
        self.sale_other_invoice_ids = sale_other_invoice_ids



    partner_id = fields.Many2one('res.partner', u'合作伙伴', domain=[('customer', '=', True)])
    yjzy_payment_id = fields.Many2one('account.payment',u'日常收款单')
    gongsi_id = fields.Many2one('gongsi', '内部公司')

    invoice_ids = fields.Many2many('account.invoice', 'ref_wz_inv', 'inv_id', 'wz_id', u'Invoice')
    so_id = fields.Many2one('sale.order','销售合同')
    so_id_currency_id = fields.Many2one('res.currency',related='so_id.currency_id')
    amount_total_so = fields.Monetary('合同金额',related='so_id.amount_total' ,currency_field='so_id_currency_id')
    btd_id = fields.Many2one('back.tax.declaration','退税申报单')
    sale_other_invoice_ids = fields.Many2many('account.invoice', 'p3_id', 'i3_id', '未完成认领其他应收',
                                              compute='compute_invoice_advance')

    currency_id = fields.Many2one('res.currency','货币', related='yjzy_payment_id.currency_id')

    ysrld_amount = fields.Monetary('预收认领金额',currency_field='currency_id')
    step = fields.Selection([('10','10'),('20','20')],'步骤',default='10')

    renling_type = fields.Selection([('yshxd', '应收认领'),
                                 ('ysrld', '预收认领'),
                                 ('back_tax', '退税认领'),('other_payment', '其他认领')], u'认领属性')

    declaration_date = fields.Date('申报日期')
    company_currency_id = fields.Many2one('res.currency', string='公司货币',  default=lambda self: self.env.user.company_id.currency_id.id,
                                          readonly=True)
    declaration_amount_all = fields.Monetary(u'本次申报金额',currency_field='company_currency_id', related = 'btd_id.declaration_amount_all')
    btd_line_ids = fields.Many2many('back.tax.declaration.line','ref_btd_id','wz_renling_id',u'申报明细')
    other_payment_invoice_ok = fields.Boolean('待认领其他应收',default=True)
    other_payment_invoice_ok_f = fields.Boolean('是否其他应付', default=False)


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
        if renling_type in ['yshxd','ysrld']:
            partner_id = False
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
        if renling_type in ['yshxd','ysrld'] and self.partner_id:

            self.step = '20'



    def apply(self):
        self.ensure_one()

        self.create_yshxd_ysrl()

    #从预收单申请应收
    def create_ysrld_yxhxd(self):
        if len(self.invoice_ids.mapped('currency_id')) > 1:
            raise Warning('不同币种的账单，不能同时认领！')
        sfk_type = 'yshxd'
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        yshxd_obj = self.env['account.reconcile.order']
        yshxd_id = yshxd_obj.create({
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
        self.make_lines_so(yshxd_id)
        yshxd_id.compute_advice_amount_advance_org()
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
                        'active_id': yshxd_id.id
                        }
        }

    def create_yshxd_ysrl(self):
        if len(self.invoice_ids.mapped('currency_id')) > 1:
            raise Warning('不同币种的账单，不能同时认领！')
        if not self.renling_type:
            raise Warning('未选择认领属性')
        if self.renling_type == 'yshxd':
            if not self.partner_id:
                raise Warning('请先选择客户')
            if not self.invoice_ids:
                raise Warning('请先选择需要认领的账单')
        if self.renling_type == 'ysrld':
            if not self.partner_id:
                raise Warning('请先选择客户')
        if self.renling_type == 'other_payment':
            if not self.partner_id:
                raise Warning('请先选择客户')
            if not self.invoice_ids and self.other_payment_invoice_ok :
                raise Warning('请先选择需要认领的账单')
        elif self.renling_type in ['back_tax'] :
            if not self.partner_id:
                raise Warning('请先选择客户')
            if not self.btd_line_ids:
                raise Warning('请先选择需要认领的退税申报')
        back_tax_declaration_id = False
        if self.renling_type in ['yshxd']:
            invoice_attribute = 'normal'
            sfk_type = 'yshxd'
            yjzy_type = 'sale'
            hxd_type_new = '20'
        elif self.renling_type == 'back_tax':
            invoice_attribute = 'normal'
            sfk_type = 'yshxd'
            yjzy_type = 'back_tax'
            back_tax_declaration_id = self.btd_id.id
            hxd_type_new = '20'
        elif self.renling_type == 'other_payment':
            invoice_attribute = 'other_payment'
            sfk_type = 'yshxd'
            yjzy_type = 'other_payment_sale'
            hxd_type_new = '20'
        else:
            invoice_attribute = False
            sfk_type = 'ysrld'

        yshxd_obj = self.env['account.reconcile.order']
        ysrld_obj = self.env['account.payment']

        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        if self.renling_type in ['yshxd','back_tax','other_payment']:
            yshxd_id = yshxd_obj.create({
                                         'name': name,
                                         'operation_wizard': '10',
                                         'partner_id': self.partner_id.id,
                                         'sfk_type': 'yshxd',
                                         'renling_type':self.renling_type,
                                         'back_tax_declaration_id':back_tax_declaration_id,
                                         'payment_type': 'inbound',
                                         'partner_type': 'customer',
                                         'yjzy_payment_id':self.yjzy_payment_id.id,
                                         'be_renling': True,
                                         'invoice_attribute': invoice_attribute,
                                         'yjzy_type': yjzy_type,
                                         'hxd_type_new':hxd_type_new

                                         })

            self.make_lines_so(yshxd_id)

            form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_new').id
            return {
                'name': '应收认领单',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.reconcile.order',
                'views': [(form_view, 'form')],
                'res_id': yshxd_id.id,
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'default_sfk_type': 'yshxd',
                            'active_id': yshxd_id.id,
                            'bank_amount': 1,
                            'show_so': 1,
                            'open':1,
                            }

            }


        elif self.renling_type in ['ysrld']:
            journal_domain = [('code', '=', 'ysdrl'), ('company_id', '=', self.env.user.company_id.id)]
            journal_id = self.env['account.journal'].search(journal_domain, limit=1)
            ysrld_amount = self.ysrld_amount
            ysrld = ysrld_obj.with_context({'bank_amount':1,'show_shoukuan': True, 'default_sfk_type': 'ysrld', 'default_payment_type': 'inbound', 'default_be_renling': True, 'default_advance_ok': True, 'default_partner_type': 'customer',}).create({
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
                'journal_id':journal_id.id,
                'so_id':self.so_id.id,


            })

            form_view = self.env.ref('yjzy_extend.view_ysrld_form_new_open').id
            return {
                'name': '应收认领单',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.payment',
                'views': [(form_view, 'form')],
                'res_id': ysrld.id,
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'default_sfk_type': 'ysrld',
                            'active_id': ysrld.id,
                            'bank_amount': 1,
                            'show_so': 1,
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

    def make_lines_so(self, yshxd_id):
        self.ensure_one()
        ctx = self.env.context
        order_id = yshxd_id  # ctx.get('active_id')
        print('order_id', order_id)
        line_obj = self.env['account.reconcile.order.line']
        line_no_obj = self.env['account.reconcile.order.line.no']

        order_id.line_ids = None
        # if self.no_sopo:
        #     for invoice in self.invoice_ids:
        #         line_obj.create({
        #             'order_id': self.id,
        #             'invoice_id': invoice.id,
        #             'amount_invoice_so': invoice.amount_total,
        #         })
        # else:
        line_ids = line_obj.browse([])
        line_id = None
        #如果是退税，就取退税申报明细的对应的发票
        if self.renling_type == 'back_tax':
            invoice_ids = self.btd_line_ids.mapped('invoice_id')
        else:
            invoice_ids = self.invoice_ids
        print('invoice_ids',invoice_ids)
        declaration_amount = 0
        if self.renling_type == 'back_tax':
            for btd in self.btd_line_ids:
                so_invlines = self._prepare_sale_invoice_line(btd.invoice_id)
                if btd.invoice_id.yjzy_type == 'back_tax' or btd.invoice_id.yjzy_type_1 == 'back_tax':
                    declaration_amount = btd.declaration_amount
                else:
                    declaration_amount = 0
                print('declaration_amount_0000000000', declaration_amount)
                if not so_invlines:
                    line_id = line_obj.create({
                        'order_id': order_id.id,
                        'invoice_id': btd.invoice_id.id,
                        'amount_invoice_so': btd.invoice_id.amount_total,
                        'amount_payment_org': declaration_amount
                    })
                line_ids |= line_id
        else:
            for invoice in invoice_ids:
                so_invlines = self._prepare_sale_invoice_line(invoice)
                if not so_invlines:
                    line_id = line_obj.create({
                        'order_id': order_id.id,
                        'invoice_id': invoice.id,
                        'amount_invoice_so': invoice.amount_total,
                        'amount_payment_org': 0
                    })
                else:
                    for so, invlines in so_invlines.items():
                        line_id = line_obj.create({
                            'order_id': order_id.id,
                            'so_id': so.id,
                            'invoice_id': invoice.id,
                            'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                            'amount_payment_org': 0,

                        })
                line_ids |= line_id
        order_id.invoice_ids = invoice_ids
        # self.order_id.invoice_attribute = self.invoice_ids[0].invoice_attribute
        self.invoice_partner = invoice_ids[0].invoice_partner
        self.name_title = invoice_ids[0].name_title
        so_po_dic = {}
        print('line_obj', line_ids)
        order_id.line_no_ids = None
        # yjzy_advance_payment_id = self.yjzy_advance_payment_id
        for i in line_ids:
            invoice = i.invoice_id
            amount_invoice_so = i.amount_invoice_so
            advance_residual2 = i.advance_residual2
            amount_payment_org = i.amount_payment_org

            order = i.order_id

            k = invoice.id

            if i.invoice_id.yjzy_type == 'back_tax' or i.invoice_id.yjzy_type_1 == 'back_tax':
                declaration_amount_1 = amount_payment_org
            else:
                declaration_amount_1 = 0
            if k in so_po_dic:
                print('k', k)
                so_po_dic[k]['amount_invoice_so'] += amount_invoice_so
                so_po_dic[k]['advance_residual2'] += advance_residual2
                so_po_dic[k]['amount_payment_org'] += declaration_amount_1
            else:
                print('k1', k)
                so_po_dic[k] = {
                    'invoice_id': invoice.id,
                    'amount_invoice_so': amount_invoice_so,
                    'advance_residual2': advance_residual2,
                    # 'yjzy_payment_id': yjzy_advance_payment_id.id
                    'amount_payment_org': declaration_amount_1,
                }

        for kk, data in list(so_po_dic.items()):
            line_no = line_no_obj.create({
                'order_id': order_id.id,
                'invoice_id': data['invoice_id'],
                'amount_invoice_so': data['amount_invoice_so'],
                'advance_residual2': data['advance_residual2'],
                # 'yjzy_payment_id': yjzy_advance_payment_id.id,
                'amount_payment_org': data['amount_payment_org'],
            })

    # def apply(self):
    #     self.ensure_one()
    #     ctx = self.env.context
    #     bill_id = ctx.get('active_id')
    #     tb = self.env['transport.bill'].browse(bill_id)
    #     sale_orders = self.so_ids
    #
    #     if len(sale_orders.mapped('partner_id')) > 1:
    #         raise Warning(u'必须是同一个客户的订单')
    #
    #     bill_line_obj = self.env['transport.bill.line']
    #     for sol in sale_orders.mapped('order_line'):
    #         if sol.qty_undelivered > 0:
    #             so = sol.order_id
    #             #so.tb_ids |= tb
    #             bill_line_obj.create({
    #                 'bill_id': bill_id,
    #                 'sol_id': sol.id,
    #                 'qty': sol.qty_undelivered,
    #                 'qty1stage': sol.qty_unreceived,
    #                 'back_tax': sol.product_id.back_tax,
    #             })
    #     return True


    def create_tb_po_invoice(self):
        form_view = self.env.ref('yjzy_extend.tb_po_form')
        type = self.renling_type
        yjzy_type_1 = self.env.context.get('default_yjzy_type_1')
        type_invoice = self.env.context.get('default_type_invoice')

        print('type_invoice',type_invoice,yjzy_type_1)

        tb_po_invoice_obj = self.env['tb.po.invoice']
        tb_po_invoice_id = tb_po_invoice_obj.create({'currency_id':self.currency_id.id,
                                                     'manual_currency_id':self.currency_id.id,
                                                     'type':type,
                                                     'yjzy_type_1':yjzy_type_1,
                                                     'type_invoice':type_invoice,
                                                     'yjzy_payment_id':self.yjzy_payment_id.id,

                                                     })
        print('tb_po_invoice_id',tb_po_invoice_id)
        return {
            'name': '其他应收申请单',
            'view_type': 'tree,form',
            "view_mode": 'form',
            'res_model': 'tb.po.invoice',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': tb_po_invoice_id.id,
            'target': 'new',
            # 'domain': [('yjzy_advance_payment_id', '=', self.id)],
            'context': {'open':1}
        }




#####################################################################################################################
