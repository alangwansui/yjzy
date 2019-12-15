# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning


class wizard_transport4so(models.TransientModel):
    _name = 'wizard.transport4so'

    partner_id = fields.Many2one('res.partner', u'客户', domain=[('customer', '=', True)])
    so_ids = fields.Many2many('sale.order', 'ref_so_tb', 'so_id', 'tb_id', u'销售订单',
                              domain="[('delivery_status', '!=', 'received'),('state', '=','sale')]")

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
