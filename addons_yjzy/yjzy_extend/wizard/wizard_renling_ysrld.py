# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning

#收款-应收认领完成后，在预收明细点创建弹窗
class wizard_renling_ysrld(models.TransientModel):
    _name = 'wizard.renling.ysrld'


    invoice_ids = fields.Many2many('account.invoice', 'ref_wzy_inv', 'inv_id', 'wzy_id', u'Invoice')
    yjzy_advance_payment_id = fields.Many2one('account.payment',u'预收认领单')
    partner_id = fields.Many2one('res.partner', u'合作伙伴', domain=[('customer', '=', True)])
    invoice_attribute = fields.Selection(
        [('normal', u'常规账单'),
         ('reconcile', u'核销账单'),  # 等待删除
         ('extra', u'额外账单'),  # 等待删除
         ('other_po', u'直接增加'),
         ('expense_po', u'费用转换'),
         ('other_payment', u'其他')], '账单属性')
    yjzy_type = fields.Selection([('sale', '销售'),
                                  ('purchase', '采购'),
                                  ('back_tax', '退税'),
                                  ('other_payment_sale', '其他应收'),  # 等待删除
                                  ('other_payment_purchase', '其他应付')  # 等待删除
                                  ], u'发票类型')
    invoice_type_main = fields.Selection([('10_main', u'常规账单'),
                                          ('20_extra', u'额外账单'),
                                          ('30_reconcile', u'核销账单')], '账单类型')




    def _make_lines_so(self):
        self.ensure_one()
        line_obj = self.env['account.reconcile.order.line']
        line_no_obj = self.env['account.reconcile.order.line.no']
        print('line_no_obj',line_no_obj)
        line_ids = None
        self.line_ids = line_ids
        # if self.no_sopo:
        #     for invoice in self.invoice_ids:
        #         line_obj.create({
        #             'order_id': self.id,
        #             'invoice_id': invoice.id,
        #             'amount_invoice_so': invoice.amount_total,
        #         })
        # else:
        for invoice in self.invoice_ids:
            so_invlines = self._prepare_sale_invoice_line(invoice)
            if not so_invlines:
                line = line_obj.create({
                    'order_id': self.id,
                    'invoice_id': invoice.id,
                    'amount_invoice_so': invoice.amount_total,
                    'amount_payment_org':invoice.declaration_amount
                })
                line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve
            else:
                for so, invlines in so_invlines.items():
                    if self.yjzy_advance_payment_id.so_id:
                        if so.id == self.yjzy_advance_payment_id.so_id.id:
                            yjzy_payment_id = self.yjzy_advance_payment_id.id
                        else:
                            yjzy_payment_id = False
                    else:
                        yjzy_payment_id = self.yjzy_advance_payment_id.id
                    line_obj.create({
                        'order_id': self.id,
                        'so_id': so.id,
                        'invoice_id': invoice.id,
                        'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                        'yjzy_payment_id': yjzy_payment_id
                    })

        so_po_dic = {}
        print('line_obj', line_ids)
        self.line_no_ids = None
        yjzy_advance_payment_id = self.yjzy_advance_payment_id
        for i in self.line_ids:
            invoice = i.invoice_id
            amount_invoice_so = i.amount_invoice_so
            advance_residual2 = i.advance_residual2
            amount_payment_org = i.amount_payment_org
            order = i.order_id
            yjzy_payment_id = i.yjzy_payment_id
            print('yjzy_payment_id_1111111', yjzy_payment_id)

            k = invoice.id
            if k in so_po_dic:
                print('k',k)
                so_po_dic[k]['amount_invoice_so'] += amount_invoice_so
                so_po_dic[k]['advance_residual2'] += advance_residual2
                so_po_dic[k]['amount_payment_org'] += amount_payment_org

                if not so_po_dic[k]['yjzy_payment_id']:
                    so_po_dic[k]['yjzy_payment_id'] = yjzy_payment_id.id
            else:
                print('k1', k)
                so_po_dic[k] = {
                                'invoice_id':invoice.id,
                                'yjzy_payment_id': yjzy_payment_id.id,
                                'amount_invoice_so': amount_invoice_so,
                                'advance_residual2': advance_residual2,
                                'amount_payment_org':amount_payment_org}



        for kk, data in list(so_po_dic.items()):
            line_no = line_no_obj.create({
                'order_id': self.id,
                'invoice_id': data['invoice_id'],
                'amount_invoice_so': data['amount_invoice_so'],
                'advance_residual2': data['advance_residual2'],
                'yjzy_payment_id': data['yjzy_payment_id'],
                'amount_payment_org':data['amount_payment_org'],
            })

            line_no.amount_payment_can_approve_all_this_time = line_no.invoice_id.amount_payment_can_approve_all
            line_no.invoice_residual_this_time = line_no.invoice_residual


    def create_hxd(self):
        sfk_type = 'yshxd'
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        yshxd_obj = self.env['account.reconcile.order']
        invoice_ids = self.invoice_ids
        print('invoice_ids_akiny',invoice_ids)
        yshxd_id = yshxd_obj.with_context({'default_invoice_ids':invoice_ids}).create({
            'name': name,
            'operation_wizard': '20',
            'yjzy_advance_payment_id': self.yjzy_advance_payment_id.id,
            'partner_id': self.partner_id.id,
            'sfk_type': sfk_type,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'be_renling': True,
            'invoice_attribute': 'normal',
            'yjzy_type': 'sale',
            'hxd_type_new': '10'
        })
        yshxd_id.with_context({'advance_payment_id': self.yjzy_advance_payment_id.id,
                             'account_payment_state_id':self.id}).make_lines_11_16()
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
                        'active_id': yshxd_id.id,
                        'open':1
                        }
        }





#####################################################################################################################
