# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning


class transport_pack_line(models.Model):
    _name = 'transport.pack.line'

    company_currency_id = fields.Many2one('res.currency', string='公司货币', related='bill_id.company_currency_id', readonly=True)
    sale_currency_id = fields.Many2one('res.currency', related='bill_id.sale_currency_id', readonly=True,
                                       string=u'交易货币', )
    third_currency_id = fields.Many2one('res.currency', related='bill_id.third_currency_id', readonly=True,
                                        string=u'统计货币')


    name = fields.Char('Name')
    type = fields.Selection([('auto', u'自动'), ('manual', '手动')], u'创建方式', default='auto')
    category_id = fields.Many2one('product.category', u'分类')
    bill_id = fields.Many2one('transport.bill', u'出运单')
    cip_type = fields.Selection(related='bill_id.cip_type', string='报关类型')
    line_ids = fields.One2many('transport.bill.line', 'pack_line_id', u'出运明细')

    product_id = fields.Many2one('product.product', u'产品', )
    hs_code = fields.Char(u'HS编码')
    hs_name = fields.Char(u'HS品名')
    hs_en_name = fields.Char(u'HS英文品名')
    pack_qty = fields.Integer(u'大包装件数')
    pack_qty1 = fields.Integer(u'大包装件数')
    pack_qty2 = fields.Integer(u'中包装件数')
    pack_qty3 = fields.Integer(u'小包装件数')

    qty = fields.Float(u'产品数量')
    gross_weight = fields.Float(u'毛重', digits=dp.get_precision('Weight'))
    net_weight = fields.Float(u'净重', digits=dp.get_precision('Weight'))
    volume = fields.Float(u'尺码m³', digits=dp.get_precision('Volume'))

    sale_amount = fields.Monetary(u'销售金额', currency_field='sale_currency_id')
    ciq_amount = fields.Monetary(u'报关金额', currency_field='sale_currency_id')
    no_ciq_amount = fields.Monetary(u'不报关金额', currency_field='sale_currency_id')

    keyword = fields.Char(u'报关要素')
    note = fields.Char(u'其他')

    source_area = fields.Char(u'原产地')
    source_country_id = fields.Many2one('res.country', '原产国')



    def _compute_one(self):
        self.ensure_one()
        package_obj = self.env['product.packaging']

        lines = self.line_ids
        products = lines.mapped('product_id')
        pdt_qty_dict = dict([(p, 0) for p in products])
        for line in lines:
            pdt_qty_dict[line.product_id] += line.qty2stage

        total_max_qty = total_mid_qty = total_min_qty = total_net_weight = total_gross_weight = total_volume = 0
        for pdt, qty in pdt_qty_dict.items():
            res = pdt.get_package_info(qty)
            total_max_qty += res['max_qty']
            total_mid_qty += res['mid_qty']
            total_min_qty += res['min_qty']

            total_net_weight += res['net_weight']
            total_gross_weight += res['gross_weight']
            total_volume += res['volume']

        return total_max_qty, total_net_weight, total_gross_weight, total_volume, total_mid_qty, total_min_qty

    @api.multi
    def compute(self):
        for one in self:
            one.qty = sum([x.qty2stage for x in one.line_ids])
            one.pack_qty, one.net_weight, one.gross_weight, one.volume, one.pack_qty2, one.pack_qty3 = one._compute_one()
            one.sale_amount = one.company_currency_id.compute(sum([x.sale_amount for x in one.line_ids]), one.sale_currency_id)

            # 正常报关：就填写报关金额（美金），买单报关：填写不报关金额（美金），不报关：两个金额都不填
            if one.cip_type == 'normal':
                one.ciq_amount = one.sale_amount
            elif one.cip_type == 'buy':
                one.no_ciq_amount = one.sale_amount
            else:
                pass
            one.source_area, one.source_country_id = one.get_source_area()

    def get_source_area(self):
        '''根据最大金额取产地信息'''
        self.ensure_one()
        source_area, source_country = None, None
        if self.line_ids:
            line = self.line_ids.sorted(key='sale_amount', reverse=True)[0]
            product = line.product_id
            source_area, source_country = product.source_area, product.source_country_id
        return (source_area, source_country)
