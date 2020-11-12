# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning


class wizard_so2po(models.TransientModel):
    _name = 'wizard.so2po'

    so_id = fields.Many2one('sale.order', u'Sale Order')
    line_ids = fields.One2many('wizard.so2po.line', 'wizard_id', u'明细')

    def check(self):
        self.ensure_one()
        for line in self.line_ids:
            # 采购数 + 总预留数 <= 销售数
            if line.qty + line.sol_id.qty_pre_all > line.sol_id.product_uom_qty:
                raise Warning('产品%s 采购数%s + 总预留数%s  超过了 销售数%s' %
                              (line.product_id.default_code, line.qty, line.sol_id.qty_pre_all, line.sol_id.product_uom_qty))
            if not line.supplier_id:
                raise Warning(u'供应商必填')

    def make_purchase_orders(self):
        self.ensure_one()
        self.check()

        po_obj = self.env['purchase.order']
        pol_obj = self.env['purchase.order.line']

        dic_partner_lines = self._prepare_po_datas()
        purchase_orders = po_obj.browse()
        for partner, lines in dic_partner_lines.items():
            po = po_obj.create({
                'partner_id': partner.id,
                'source_so_id': self.so_id.id,
                'date_planned': self.so_id.requested_date,
                'gongsi_id': self.so_id.purchase_gongsi_id.id,
            })
            for line in lines:
                pol = pol_obj.create({
                    'order_id': po.id,
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_qty': line.qty,
                    'product_uom': line.product_id.uom_id.id,
                    'date_planned': self.so_id.requested_date,
                    'price_unit': line.sol_id.purchase_price,
                    'sol_id': line.sol_id.id,
                    'lot_sub_name': line.sol_id.lot_sub_name,
                    'back_tax': line.sol_id.back_tax,
                })
                line.sol_id.pol_id = pol

            po.date_planned = self.so_id.requested_date
            po.onchange_partner_id()
            po.create_lots()
            po.action_sale_reserve()
            purchase_orders |= po
        form_view = self.env.ref('yjzy_extend.new_purchase_order_from')
        tree_view = self.env.ref('yjzy_extend.new_purchase_order_tree')
        return {
            'name': _(u'创建采购单'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            # 'target': 'new',
            'domain': [('id', '=', purchase_orders.mapped('id'))],
            # 'context': { },
        }

    def _prepare_po_datas(self):
        dic_partner_lines = {}  # {partner:  wizard_line}
        for line in self.line_ids:
            supplier = line.supplier_id
            if supplier in dic_partner_lines:
                dic_partner_lines[supplier].append(line)
            else:
                dic_partner_lines.update({supplier: [line]})
        return dic_partner_lines


class wizard_so2po_line(models.TransientModel):
    _name = 'wizard.so2po.line'

    wizard_id = fields.Many2one('wizard.so2po', 'Wizard')
    sol_id = fields.Many2one('sale.order.line', u'销售明细')
    product_id = fields.Many2one('product.product', u'产品', related='sol_id.product_id')
    sale_qty = fields.Float(related='sol_id.product_uom_qty', string=u'销售数')
    smline_qty = fields.Float(related='sol_id.smline_qty', string=u'已锁定数')

    qty_available = fields.Float(related='product_id.qty_available', string=u'在手数')
    virtual_available = fields.Float(related='product_id.virtual_available', string=u'预测数')
    supplier_id = fields.Many2one('res.partner', u'供应商', domain=[('supplier', '=', True)])
    purchase_price = fields.Float('采购价格', related='sol_id.purchase_price')
    qty = fields.Float(u'采购数量')

    @api.constrains('qty', 'supplier_id')
    def check(self):
        if self.qty < 0:
            raise Warning(u'采购数量不能小于0')
