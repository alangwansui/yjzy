# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning


class wizard_transport4so(models.TransientModel):
    _name = 'wizard.transport4so'

    def compute_sale_order(self):
        return self.sol_ids.mapped('order_id')

    partner_id = fields.Many2one('res.partner', u'客户', domain=[('customer', '=', True)])
    gongsi_id = fields.Many2one('gongsi', '内部公司')
    purchase_gongsi_id = fields.Many2one('gongsi', '内部采购公司')
    so_ids = fields.Many2many('sale.order', 'ref_so_tb', 'so_id', 'tb_id', u'销售订单')

    sol_ids = fields.Many2many('sale.order.line', 'ref_soline_tb', 'sol_id', 'tb_id', u'销售明细')
    sale_order_ids = fields.Many2many('sale.order', string='销售订单')

    incoterm = fields.Many2one('stock.incoterms', '价格条款')
    payment_term_id = fields.Many2one('account.payment.term', string='付款条款')
    include_tax = fields.Boolean(u'含税')
    currency_id = fields.Many2one('res.currency', string=u'交易货币')





    def check_same(self):
        ctx ={
            'default_partner_id': self.partner_id.id,
            'default_gongsi_id': self.gongsi_id.id,
            'default_purchase_gongsi_id': self.purchase_gongsi_id.id,
            'check_same': True,
            'add_sol':False,
            'active_id': self.env.context.get('active_id'),
        }
        return {
            'name': '添加销售明细',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.transport4so',
            'res_id': self.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': ctx,
        }



    def _check_same(self):
        self.sale_order_ids = self.sol_ids.mapped('order_id')
        same_incoterm = self.sale_order_ids.mapped('incoterm')
        same_payment_term = self.sale_order_ids.mapped('payment_term_id')
        same_currency = self.sale_order_ids.mapped('currency_id')
        same_include_tax = self.sale_order_ids.mapped('include_tax')
        print('---',same_incoterm,same_payment_term,same_currency,same_include_tax,len(same_incoterm),len(same_payment_term),len(same_currency),len(set(same_include_tax)))
        self.incoterm = same_incoterm and same_incoterm[0]
        self.payment_term_id = same_payment_term and same_payment_term[0]
        self.currency_id = same_currency and same_currency[0]
        self.include_tax = same_include_tax and same_include_tax[0]
        # return all([len(same_incoterm) == 1, len(same_payment_term) == 1, len(same_currency) == 1, len(set(same_include_tax)) == 1])
        return False

    def check_apply(self):
        ctx = self.env.context
        bill_id = ctx.get('active_id')
        tb = self.env['transport.bill'].browse(bill_id)
        sale_lines = self.sol_ids
        if len(sale_lines.mapped('order_id').mapped('partner_id')) > 1:
            raise Warning(u'必须是同一个客户的订单')

        bill_line_obj = self.env['transport.bill.line']
        tblines = bill_line_obj.browse([])
        for sol in sale_lines:
            if sol.qty_undelivered > 0:
                tbl = bill_line_obj.create({
                    'bill_id': bill_id,
                    'sol_id': sol.id,
                    'qty': sol.qty_undelivered,
                    'qty1stage': sol.qty_unreceived,
                    'back_tax': sol.product_id.back_tax,
                    'so_tb_number': sol.order_id.tb_count + 1,
                })
                tblines |= tbl

        tb.check_lines()
        #自动安排调拨计划
        tb.incoterm = self.incoterm
        tb.payment_term_id = self.payment_term_id
        tb.sale_currency_id = self.currency_id
        tb.include_tax = self.include_tax
        tblines.make_default_lot_plan()
        tb.is_done_plan = True
        return True

    def check_apply_continue(self):
        ctx = self.env.context
        bill_id = ctx.get('active_id')
        tb = self.env['transport.bill'].browse(bill_id)
        sale_lines = self.sol_ids
        if len(sale_lines.mapped('order_id').mapped('partner_id')) > 1:
            raise Warning(u'必须是同一个客户的订单')

        bill_line_obj = self.env['transport.bill.line']
        tblines = bill_line_obj.browse([])
        for sol in sale_lines:
            if sol.qty_undelivered > 0:
                tbl = bill_line_obj.create({
                    'bill_id': bill_id,
                    'sol_id': sol.id,
                    'qty': sol.qty_undelivered,
                    'qty1stage': sol.qty_unreceived,
                    'back_tax': sol.product_id.back_tax,
                    'so_tb_number': sol.order_id.tb_count + 1,
                })
                tblines |= tbl

        tb.check_lines()
        #自动安排调拨计划
        tb.incoterm = self.incoterm
        tb.payment_term_id = self.payment_term_id
        tb.sale_currency_id = self.currency_id
        tb.include_tax = self.include_tax
        tblines.make_default_lot_plan()
        tb.is_done_plan = True
        return tb.edit_line_ids()


    def new_apply(self):
        self.ensure_one()
        if not self._check_same():
            return self.check_same()


        ctx = self.env.context
        bill_id = ctx.get('active_id')
        tb = self.env['transport.bill'].browse(bill_id)
        sale_lines = self.sol_ids

        if len(sale_lines.mapped('order_id').mapped('partner_id')) > 1:
            raise Warning(u'必须是同一个客户的订单')

        bill_line_obj = self.env['transport.bill.line']
        tblines = bill_line_obj.browse([])
        for sol in sale_lines:
            if sol.qty_undelivered > 0:
                tbl =bill_line_obj.create({
                    'bill_id': bill_id,
                    'sol_id': sol.id,
                    'qty': sol.qty_undelivered,
                    'qty1stage': sol.qty_unreceived,
                    'back_tax': sol.product_id.back_tax,
                    'so_tb_number':sol.order_id.tb_count+1,
                })
                tblines |= tbl
        tb.check_lines()
        tblines.make_default_lot_plan()
        tb.is_done_plan = True
        return True

    def apply(self):
        self.ensure_one()
        ctx = self.env.context
        bill_id = ctx.get('active_id')
        tb = self.env['transport.bill'].browse(bill_id)
        sale_orders = self.so_ids

        if len(sale_orders.mapped('partner_id')) > 1:
            raise Warning(u'必须是同一个客户的订单')

        bill_line_obj = self.env['transport.bill.line']
        for sol in sale_orders.mapped('order_line'):
            if sol.qty_undelivered > 0:
                so = sol.order_id
                #so.tb_ids |= tb
                bill_line_obj.create({
                    'bill_id': bill_id,
                    'sol_id': sol.id,
                    'qty': sol.qty_undelivered,
                    'qty1stage': sol.qty_unreceived,
                    'back_tax': sol.product_id.back_tax,
                })
        return True




#####################################################################################################################
