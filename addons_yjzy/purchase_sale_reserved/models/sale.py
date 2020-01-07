# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning

class sale_order(models.Model):
    _inherit = 'sale.order'

    def compute_purchase_order(self):
        for one in self:
            one.po_ids = one.order_line.mapped('dlr_ids').mapped('po_id')
            one.po_count = one.po_ids and len(one.po_ids) or 0

    po_ids = fields.Many2many('purchase.order', string=u'采购订单', compute=compute_purchase_order)
    po_count = fields.Integer(u'采购单数量', compute=compute_purchase_order)
    dump_picking_id = fields.Many2one('stock.picking', u'虚拟预留', copy=False)

    def action_confirm(self):
        self.undo_dump_reserve()
        res = super(sale_order,self).action_confirm()
        #TODO 保证确认预留内容和 虚拟预留的批次，数量一致
        return res

    def make_dump_reserve(self):
        self.ensure_one()
        dump_picking = self.dump_picking_id
        if not dump_picking:
            move_obj = self.env['stock.move']
            picking_type = self.env['stock.picking.type'].search([('ref', '=', 'sale_reserve'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if not picking_type:
                raise Warning(u'没有定义销售预留的调拨类型，请联系管理员')
            dump_picking = self.env['stock.picking'].create({
                'name': picking_type.sequence_id.next_by_id(),
                'partner_id': self.partner_id.id,
                'picking_type_id': picking_type.id,
                'location_id': picking_type.default_location_src_id.id,
                'location_dest_id': picking_type.default_location_dest_id.id,
            })
            for sol in self.order_line:
                move_obj.create({
                    'name': sol.name,
                    'picking_id': dump_picking.id,
                    'product_id': sol.product_id.id,
                    'product_uom': sol.product_id.uom_id.id,
                    'product_uom_qty': sol.product_uom_qty,
                    'location_id': picking_type.default_location_src_id.id,
                    'location_dest_id': picking_type.default_location_dest_id.id,
                })
            self.dump_picking_id = dump_picking
        dump_picking.action_assign()

    def undo_dump_reserve(self):
        self.ensure_one()
        if self.dump_picking_id:
            self.dump_picking_id.action_cancel()
            self.dump_picking_id.unlink()

    def action_cancel(self):
        for one in self:
            one.po_ids.button_cancel()
        return super(sale_order, self).action_cancel()

    def open_wizard_so2po(self):
        self.ensure_one()
        wizard = self.env['wizard.so2po'].create({'so_id': self.id})
        view = self.env.ref('purchase_sale_reserved.wizard_wizard_so2po_form')

        line_obj = self.env['wizard.so2po.line']
        info_obj = self.env["product.supplierinfo"]

        for sol in self.order_line:
            qty = sol.product_qty - sol.smline_qty
            if qty <= 0:
                continue
            supplierinfos = info_obj.search([('product_id', '=', sol.product_id.id)], limit=1)
            line_obj.create({
                'wizard_id': wizard.id,
                'sol_id': sol.id,
                'supplier_id': supplierinfos and supplierinfos[0].name.id or False,
                'qty': qty,
            })

        return {
            'name': _(u'创建采购单'),
            'view_type': 'tree,form',
            "view_mode": 'form',
            'res_model': 'wizard.so2po',
            'type': 'ir.actions.act_window',
            'view_id': view.id,
            'target': 'new',
            'res_id': wizard.id,
            # 'context': { },
        }

    def open_purchase_order(self):
        self.ensure_one()
        return {
            'name': _(u'采购订单'),
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'domain': [('id', '=', [x.id for x in self.po_ids])],
        }

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    @api.depends('move_ids','dlr_ids')
    def compute_info(self):
        for one in self:
            smlines = one.move_ids.mapped('move_line_ids') + one.order_id.dump_picking_id.move_line_ids.filtered(lambda x:x.product_id == one.product_id)
            smline_str = '\n'.join(['%s:%s' % (x.lot_id.name, x.product_uom_qty) for x in smlines])
            one.smline_ids = smlines
            one.smline_str = smline_str
            one.smline_qty = sum([x.product_uom_qty for x in smlines])

            dlrs = one.dlr_ids
            dlrs.compute_info()

            one.dlr_str = '\n'.join([x.name or '' for x in dlrs])
            one.dlr_qty = sum([x.qty for x in dlrs])
            one.dlr_done_qty = sum([x.done_qty for x in dlrs])
            one.dlr_todo_qty = sum([x.todo_qty for x in dlrs])
            one.supplier_ids = dlrs.mapped('lot_id').mapped('supplier_id')

            qty_pre_all = one.smline_qty + one.dlr_qty
            one.qty_pre_all = qty_pre_all


    # def compute_moveline(self):
    #     for one in self:
    #         smlines = one.move_ids.mapped('move_line_ids') + one.order_id.dump_picking_id.move_line_ids.filtered(lambda x:x.product_id == one.product_id)
    #         smline_str = '\n'.join(['%s:%s' % (x.lot_id.name, x.product_uom_qty) for x in smlines])
    #         one.smline_ids = smlines
    #         one.smline_str = smline_str
    #         one.smline_qty = sum([x.product_uom_qty for x in smlines])
    #
    # @api.depends('dlr_ids')
    # def compute_dlr(self):
    #     for one in self:
    #         one.dlr_str = '\n'.join([x.name or '' for x in one.dlr_ids])
    #         one.dlr_qty = sum([x.qty for x in one.dlr_ids])
    #         one.dlr_done_qty = sum([x.done_qty for x in one.dlr_ids])
    #         one.dlr_todo_qty = sum([x.todo_qty for x in one.dlr_ids])
    #         one.supplier_ids = one.dlr_ids.mapped('lot_id').mapped('supplier_id')



    smline_ids = fields.One2many('stock.move.line', compute=compute_info, string=u'库存预留')
    smline_str = fields.Char(compute=compute_info, string=u'锁定内容')
    smline_qty = fields.Float(compute=compute_info, string=u'锁定总数')

    dlr_ids = fields.One2many('dummy.lot.reserve', 'sol_id', string=u'采购预留')
    supplier_ids = fields.Many2many('res.partner', compute=compute_info, string='供应商')
    dlr_str = fields.Char(compute=compute_info, string=u'采购预留')
    dlr_qty = fields.Float(compute=compute_info, string=u'采购预留数')
    dlr_done_qty = fields.Float(compute=compute_info, string=u'预留完成数')
    dlr_todo_qty = fields.Float(compute=compute_info, string=u'待预留数')

    qty_pre_all = fields.Float(compute=compute_info, string=u'预留总数')


    def open_wizard_sol_reserver(self):
        self.ensure_one()

        item_obj = self.env['wizard.sol.reserver.item']
        wizard = self.env['wizard.sol.reserver'].create({'sol_id': self.id})

        for dlr in  self.env['dummy.lot.reserve'].search([('sol_id','=',self.id)]):
            item = item_obj.create({
                'wizard_id': wizard.id,
                'dlr_id': dlr.id,
            })
            item.onchange_dlr()


        return {
            'name': u'采购预留',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.sol.reserver',
            'res_id': wizard.id,
            'type': 'ir.actions.act_window',
            'target': 'new',

        }





