# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning


class transport_qingguan_line(models.Model):
    _name = 'transport.qingguan.line'
    _rec_name = 'product_id'


    @api.depends()
    def compute_price(self):
        for one in self:
            if one.qty > 0:
                one.price = one.sub_total / one.qty
            else:
                pass


    def compute_shiji(self):
        for one in self:
            one.shiji_weight = one.gross_weight + one.tuopan_weight
            one.shiji_volume = one.volume + one.tuopan_volume




    tb_id = fields.Many2one('transport.bill', u'发运单据', required=True, ondelete='cascade')
    so_id = fields.Many2one('sale.order', u'销售订单')

    company_currency_id = fields.Many2one(related='tb_id.company_currency_id', readonly=True, )
    sale_currency_id = fields.Many2one(related='tb_id.sale_currency_id', readonly=True)
    third_currency_id = fields.Many2one(related='tb_id.third_currency_id', readonly=True)

    product_id = fields.Many2one('product.product', u'产品')
    source_area = fields.Char(u'原产地')
    source_country_id = fields.Many2one('res.country', u'原产国')
    qty = fields.Float(u'数量')

    qty_package = fields.Float(u'数量/大包装', digits=dp.get_precision('Package'))
    package_qty = fields.Float(u'大包装/数量', digits=dp.get_precision('Package'))
    gross_weight = fields.Float(u'毛重', digits=dp.get_precision('Weight'))
    net_weight = fields.Float(u'净重', digits=dp.get_precision('Weight'))
    volume = fields.Float(u'尺码m³', digits=dp.get_precision('Volume'))

    uom_id = fields.Many2one(related='product_id.uom_id', readonly=True, string=u'单位')
    price = fields.Monetary(u'单价', currency_field='sale_currency_id', compute=compute_price)
    sub_total = fields.Monetary(u'小计', currency_field='sale_currency_id', digits=dp.get_precision('Money'))

    supplier_id = fields.Many2one('res.partner', u'供应商业')

    tuopan_weight = fields.Float(u'托盘分配重量')
    tuopan_volume = fields.Float(u'托盘分配体积')
    shiji_weight = fields.Float(u'实际毛重', compute=compute_shiji, digits=dp.get_precision('Weight'))
    shiji_volume = fields.Float(u'实际体积', compute=compute_shiji, digits=dp.get_precision('Volume'))

    s_uom_id = fields.Many2one('product.uom', u'销售打印单位')


    @api.onchange('product_id')
    def onchage_product(self):
        self.s_uom_id = self.product_id.s_uom_id


    def compute_info(self):
        for one in self:
            one.source_area = one.product_id.source_area
            one.source_country_id = one.product_id.source_country_id

            pack_info = one.product_id.get_package_info(one.qty)
            one.qty_package = pack_info['max_package']
            one.package_qty = pack_info['max_qty']
            one.net_weight = pack_info['net_weight']
            one.gross_weight = pack_info['gross_weight']
            one.volume = pack_info['volume']
