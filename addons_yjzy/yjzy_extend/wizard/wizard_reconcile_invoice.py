# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning


class wizard_reconcile_invoice(models.TransientModel):
    _name = 'wizard.reconcile.invoice'


    partner_id = fields.Many2one('res.partner', u'合作伙伴', domain=[('customer', '=', True)])
    gongsi_id = fields.Many2one('gongsi', '内部公司')
    purchase_gongsi_id = fields.Many2one('gongsi', '内部采购公司')
    invoice_ids = fields.Many2many('account.invoice', 'ref_rec_inv', 'inv_id', 'tb_id', u'Invoice')
    order_id = fields.Many2one('account.reconcile.order',u'核销单')


    def apply(self):
        self.ensure_one()
        ctx = self.env.context
        sfk_type = ctx.get('sfk_type')
        print('ctx', ctx)
        if sfk_type == 'yshxd':
            self.make_lines_so()
        if sfk_type == 'yfhxd':
            self.make_lines_po()

    def make_lines_po(self):
        self.ensure_one()
        line_obj = self.env['account.reconcile.order.line']
        line_no_obj = self.env['account.reconcile.order.line.no']
        ctx = self.env.context
        order_id = ctx.get('active_id')
        # line_ids = None
        # self.line_ids = line_ids

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
        for invoice in self.invoice_ids:
            po_invlines = self._prepare_purchase_invoice_line(invoice)
            if not po_invlines:
                line_id =line_obj.create({
                    'order_id': order_id,
                    'invoice_id': invoice.id,
                    'amount_invoice_so': invoice.amount_total,
                })
            else:
                for po, invlines in po_invlines.items():
                    line_id=line_obj.create({
                        'order_id': order_id,
                        'po_id': po.id,
                        'invoice_id': invoice.id,
                        'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                    })
            line_ids |= line_id
        # 826
        self.order_id.invoice_ids = self.invoice_ids
        so_po_dic = {}
        print('line_obj', line_ids)
        self.line_no_ids = None
        for i in line_ids:
            invoice = i.invoice_id
            amount_invoice_so = i.amount_invoice_so
            advance_residual = i.advance_residual
            order = i.order_id

            k = invoice.id
            if k in so_po_dic:
                print('k', k)
                so_po_dic[k]['amount_invoice_so'] += amount_invoice_so
                so_po_dic[k]['advance_residual'] += advance_residual
            else:
                print('k1', k)
                so_po_dic[k] = {
                    'invoice_id': invoice.id,
                    'amount_invoice_so': amount_invoice_so,
                    'advance_residual': advance_residual, }

        for kk, data in list(so_po_dic.items()):
            line_no = line_no_obj.create({
                'order_id': order_id,
                'invoice_id': data['invoice_id'],
                'amount_invoice_so': data['amount_invoice_so'],
                'advance_residual': data['advance_residual'],
            })

    def _prepare_purchase_invoice_line(self, inv):
        self.ensure_one()
        dic_po_invl = {}
        for line in inv.invoice_line_ids:
            if line.purchase_id:
                po = line.purchase_id
                if po in dic_po_invl:
                    dic_po_invl[po] |= line
                else:
                    dic_po_invl[po] = line
        return dic_po_invl

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

    def make_lines_so(self):
        self.ensure_one()
        ctx = self.env.context
        order_id = ctx.get('active_id')
        line_obj = self.env['account.reconcile.order.line']
        line_no_obj = self.env['account.reconcile.order.line.no']
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
        line_ids = line_obj.browse([])
        line_id = None
        for invoice in self.invoice_ids:
            so_invlines = self._prepare_sale_invoice_line(invoice)
            if not so_invlines:
                line_id=line_obj.create({
                    'order_id': order_id,
                    'invoice_id': invoice.id,
                    'amount_invoice_so': invoice.amount_total,
                })
            else:
                for so, invlines in so_invlines.items():
                  line_id = line_obj.create({
                        'order_id': order_id,
                        'so_id': so.id,
                        'invoice_id': invoice.id,
                        'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                    })
            line_ids |= line_id
        self.order_id.invoice_ids = self.invoice_ids
        so_po_dic = {}
        print('line_obj', line_ids)
        # self.line_no_ids = None
        for i in line_ids:
            invoice = i.invoice_id
            amount_invoice_so = i.amount_invoice_so
            advance_residual2 = i.advance_residual2
            order = i.order_id

            k = invoice.id
            if k in so_po_dic:
                print('k',k)
                so_po_dic[k]['amount_invoice_so'] += amount_invoice_so
                so_po_dic[k]['advance_residual2'] += advance_residual2
            else:
                print('k1', k)
                so_po_dic[k] = {
                                'invoice_id':invoice.id,
                                'amount_invoice_so': amount_invoice_so,
                                'advance_residual2': advance_residual2,}

        for kk, data in list(so_po_dic.items()):
            line_no = line_no_obj.create({
                'order_id': order_id,
                'invoice_id': data['invoice_id'],
                'amount_invoice_so': data['amount_invoice_so'],
                'advance_residual2': data['advance_residual2'],
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




#####################################################################################################################
