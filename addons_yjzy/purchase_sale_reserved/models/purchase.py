# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning

class purchase_order(models.Model):
    _inherit = 'purchase.order'

    source_so_id = fields.Many2one('sale.order', string=u'源销售', copy=False, help=u'采购是位了这个SO，确认的时候自动分配该销售的采购预定')
    dump_picking_id = fields.Many2one('stock.picking', u'虚拟入库', copy=False, help="为了正确计算可用数量，采购先做一个入库操作")


    def make_dump_income_picking(self):
        self.ensure_one()

        dump_picking = self.dump_picking_id

        if not dump_picking:
            move_obj = self.env['stock.move']
            picking_type = self.env['stock.picking.type'].search([('ref', '=', 'dump_income'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if not picking_type:
                raise Warning(u'没有定义 虚拟入库 的调拨类型dump_income，请联系管理员')
            dump_picking = self.env['stock.picking'].create({
                'name': picking_type.sequence_id.next_by_id(),
                'partner_id': self.partner_id.id,
                'picking_type_id': picking_type.id,
                'location_id': picking_type.default_location_src_id.id,
                'location_dest_id': picking_type.default_location_dest_id.id,
            })
            for pol in self.order_line:
                move_obj.create({
                    'name': pol.name,
                    'picking_id': dump_picking.id,
                    'product_id': pol.product_id.id,
                    'product_uom': pol.product_id.uom_id.id,
                    'product_uom_qty': pol.product_uom_qty,
                    'location_id': picking_type.default_location_src_id.id,
                    'location_dest_id': picking_type.default_location_dest_id.id,
                })
            self.dump_picking_id = dump_picking
        dump_picking.action_assign()


    def button_confirm(self):
        res = super(purchase_order, self).button_confirm()
        return res

    def button_cancel(self):
        res = super(purchase_order, self).button_cancel()
        for po in self:
            dlrs = self.env['dummy.lot.reserve'].search([('po_id', '=', po.id)])
            dlrs.unlink()
            lots = self.env['stock.production.lot'].search([('po_id', '=', po.id)])
            lots.unlink()
        return res


    def create_lots(self):
        self.ensure_one()
        lot_obj = self.env['stock.production.lot']
        for line in self.order_line:
            if not lot_obj.search([('pol_id', '=', line.id)]):

                lot_name = self.name
                if line.lot_sub_name:
                    lot_name += line.lot_sub_name


                lot = lot_obj.create({
                    'name': lot_name,
                    'product_id': line.product_id.id,
                    'pol_id': line.id,
                    'dummy_qty': line.product_qty,
                })
                print ('>>>>>>>>>>>>>>>>>', lot)

    def action_sale_reserve(self):
        drl_obj = self.env['dummy.lot.reserve']
        lot_obj = self.env['stock.production.lot']
        for po in self:
            if po.source_so_id:
                so = po.source_so_id
                for sol in so.order_line:
                    if sol.lot_sub_name:
                        lot = lot_obj.search([('product_id', '=', sol.product_id.id), ('name', '=', po.name + sol.lot_sub_name)])
                    else:
                        lot = lot_obj.search([('product_id', '=', sol.product_id.id), ('po_id', '=', po.id)])
                    if lot:
                        print('===', min(lot.dummy_qty, sol.product_uom_qty), lot.dummy_qty, sol.product_uom_qty)
                        drl_obj.create({
                            'sol_id': sol.id,
                            'lot_id': lot.id,
                            'qty': min(lot.dummy_qty, sol.product_uom_qty),
                        })


class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'

    def compute_dlr(self):
        for one in self:
            dlr_ids = one.dlr_ids
            sale_names = ['%s:%s' % (x.sol_id.order_id.name, x.qty) for x in dlr_ids]
            dlr_qty = sum([x.qty for x in one.dlr_ids])

            one.dlr_str = '\n'.join(sale_names)
            one.dlr_qty = dlr_qty
            one.dlr_no_qty = one.product_qty - dlr_qty

            if one.dlr_no_qty < 0:
                raise Warning(u'锁定数量不能大于采购数量')

    dlr_ids = fields.One2many('dummy.lot.reserve', 'pol_id', string=u'销售预留')
    dlr_str = fields.Char(compute=compute_dlr, string=u'销售预留')
    dlr_qty = fields.Float(compute=compute_dlr, string=u'被预留')
    dlr_no_qty = fields.Float(compute=compute_dlr, string=u'待预留')

    lot_sub_name = fields.Char('批次区分码')
