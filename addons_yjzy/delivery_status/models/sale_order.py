from odoo import models, fields, api, _

Delivery_Status = [
    ('undelivered', u'未发货'),
    ('partially_delivered', u'部分发货'),
    ('received', u'发货完成')]


class SaleOrderDelivery(models.Model):
    _inherit = 'sale.order'

    delivery_status = fields.Selection(Delivery_Status, u"发货状态", copy=False, compute='show_delvery_status', store=True)

    @api.depends('picking_ids', 'picking_ids.state')
    def show_delvery_status(self):
        for one in self:
            if one.delivery_count > 0:
                #obj_picking = self.picking_ids
                total = 0
                cant_my = 0
                one.delivery_status = "undelivered"
                for pick in one.picking_ids:
                    total += 1
                    if pick.state == 'done':
                        cant_my += 1

                if cant_my < total:
                    one.delivery_status = "partially_delivered"

                if cant_my == 0:
                    one.delivery_status = "undelivered"

                if cant_my == total:
                    one.delivery_status = "received"

