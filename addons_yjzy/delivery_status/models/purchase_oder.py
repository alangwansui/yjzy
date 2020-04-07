from odoo import models, fields, api, _

from . sale_order import Delivery_Status


class purchase_order(models.Model):
    _inherit = 'purchase.order'

    delivery_status = fields.Selection(Delivery_Status, u"发货状态", copy=False, compute='show_delvery_status')

    @api.one
    def show_delvery_status(self):
        total = 0
        cant_my = 0
        self.delivery_status = "undelivered"
        for pick in self.picking_ids:
            total += 1
            if pick.state == 'done':
                cant_my += 1

        if cant_my < total:
            self.delivery_status = "partially_delivered"

        if cant_my == 0:
            self.delivery_status = "undelivered"

        if cant_my == total and cant_my !=0 :
            self.delivery_status = "received"