# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PurchasePaymentAdvanceTool(models.TransientModel):
    _name = 'purchase.payment.advance.tool'
    _description = '预付款查询小工具'

    def default_invoice_ids(self):
        po_id = self.env.context.get('default_po_id')
        inv_line_obj = self.env['account.invoice.line']
        inv_line_ids = inv_line_obj.search([('purchase_id','=',po_id)])
        invoice_ids = inv_line_ids.mapped('invoice_id')
        return invoice_ids

    def default_po_ids(self):
        po_id = self.env.context.get('default_po_id')
        inv_line_obj = self.env['account.invoice.line']
        inv_line_ids = inv_line_obj.search([('purchase_id','=',po_id)])
        invoice_ids = inv_line_ids.mapped('invoice_id')
        invoice_line_ids_new = inv_line_ids
        for one in invoice_ids:
            invoice_line_ids_new += one.invoice_line_ids

        po_ids = invoice_line_ids_new.mapped('purchase_id')
        print('invoice_line_ids_new_akiny', invoice_line_ids_new, po_ids)
        # po_ids_dic = []
        # for one in invoice_line_ids_new:
        #     po_ids_dic.append(one.invoice_line_ids.mapped('purchase_id'))
        # print('invoice_ids_akiny',  po_ids_dic)
        # po_obj = self.env['purchase.order']
        # po_ids = po_obj.search([('id','in',po_ids_dic)])
        #
        return po_ids
    #
    # self.ensure_one()
    # dic_po_invl = {}
    # for line in inv.invoice_line_ids:
    #     if line.purchase_id:
    #         po = line.purchase_id
    #         if po in dic_po_invl:
    #             dic_po_invl[po] |= line
    #         else:
    #             dic_po_invl[po] = line
    # return dic_po_invl or False


    def compute_purchase_amount(self):
        for one in self:
            purchase_amount = sum(x.amount_total for x in one.po_ids)
            real_advance_purchase = sum(x.real_advance for x in one.po_id)
            amount_payment_org_done = sum(x.amount_payment_org_done for x in one.invoice_ids)
            can_apply_amount = purchase_amount - real_advance_purchase - amount_payment_org_done
            print('purchase_amount_akiny',purchase_amount)
            one.purchase_amount = purchase_amount
            one.real_advance_purchase = real_advance_purchase
            one.amount_payment_org_done = amount_payment_org_done
            one.can_apply_amount = can_apply_amount


    tb_ids = fields.Many2many('transport.bill',)
    invoice_ids = fields.Many2many('account.invoice',default=lambda self: self.default_invoice_ids())
    po_ids = fields.Many2many('purchase.order',default=lambda self: self.default_po_ids())
    po_id = fields.Many2one('purchase.order','本次申请的采购合同')
    partner_id = fields.Many2one('res.partner','本次申请的供应商')

    purchase_amount = fields.Float('原始采购金额',compute=compute_purchase_amount)
    real_advance_purchase = fields.Float('预付金额',compute=compute_purchase_amount)
    amount_payment_org_done = fields.Float('付款金额',compute=compute_purchase_amount)
    can_apply_amount = fields.Float('最大付款金额',compute=compute_purchase_amount)



