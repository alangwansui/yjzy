# -*- coding: utf-8 -*-
from num2words import num2words
from odoo import models, fields, api, _
from odoo.exceptions import Warning



class transport_bill_vendor(models.Model):
    _name = 'transport.bill.vendor'
    _description = '供应商发运单'
    _rec_name = 'partner_id'

    tb_id = fields.Many2one('transport.bill', u'发货单')
    partner_id = fields.Many2one('res.partner', u'供应商')
    contact_id = fields.Many2one('res.partner', u'联系人')
    delivery_note = fields.Text('发货备注')
    delivery_type = fields.Selection([('a','我司仓库'),('b','码头仓库'),('c','装柜柜型')], '发货类型')
    delivery_type_c_info = fields.Text('柜型要求')

    tbl_lot_ids = fields.One2many('bill.line.lot', 'tbv_id', u'发货单明细批次')
    company_id = fields.Many2one('res.company', related='tb_id.company_id', string='公司', readonly=True)
    line_ids = fields.One2many('transport.bill.vendor.line', 'tbv_id', u'明细')


    @api.onchange('partner_id')
    def onchange_partner(self):
        if self.partner_id:
            self.contact_id = self.partner_id.child_ids and self.partner_id.child_ids[0] or False
        else:
            self.contact_id = False

    def make_lines(self):
        line_obj = self.env['transport.bill.vendor.line']
        dic_pdt_plan = {}  #{'product': 'plans'， 'po_amount': 0}
        for plan in self.tb_id.line_ids.mapped('lot_plan_ids').filtered(lambda x: x.stage_1 and x.lot_id.supplier_id == self.partner_id):
            product = plan.lot_id.product_id
            if product in dic_pdt_plan:
                dic_pdt_plan[product] |= plan
            else:
                dic_pdt_plan[product] = plan

        for pdt, plans in dic_pdt_plan.items():
            l = line_obj.create({
                'tbv_id': self.id,
                'product_id': pdt.id,
                'qty': sum([x.qty for x in plans]),
                'po_contract_code': ','.join(plans.mapped('lot_id').mapped('po_id').mapped('contract_code')),
                'po_amount': sum([x.lot_id.purchase_price * x.qty for x in plans])
            })
            l.compute_info()

class transport_bill_vendor(models.Model):
    _name = 'transport.bill.vendor.line'
    _description = '供应商发运单明细'

    tbv_id = fields.Many2one('transport.bill.vendor', u'供应商发运单')
    partner_id = fields.Many2one('res.partner', u'供应商', related='tbv_id.partner_id')
    product_id = fields.Many2one('product.product', u'产品')
    po_contract_code = fields.Char(u'合同号')
    supplier_code = fields.Char('应商产品代码')
    default_code = fields.Char('产品内部编号', related='product_id.default_code')
    qty = fields.Float(u'数量')
    max_qty = fields.Float(u'包数')
    gross_weight = fields.Float(u'毛重', digits=(4, 2))
    net_weight = fields.Float(u'净重')
    volume = fields.Float(u'尺码m³')
    po_amount = fields.Float(u'采购金额')

    def compute_info(self):
        for one in self:
            res = one.product_id.get_package_info(one.qty)
            one.gross_weight = res['gross_weight']
            one.net_weight  = res['net_weight']
            one.volume = res['volume']
            one.max_qty = res['max_qty']
            info = self.env['product.supplierinfo'].search([('product_id','=',one.product_id.id),('name','=',one.partner_id.id)], limit=1)
            one.supplier_code = info and info.product_code





        # return  {
        #     'max_package': max_package_qty,
        #     'mid_package': mid_package_qty,
        #     'min_package': min_package_qty,
        #     'max_qty': max_qty,
        #     'mid_qty': mid_qty,
        #     'min_qty': min_qty,
        #     'net_weight': net_weight,
        #     'gross_weight': gross_weight,
        #     'volume': volume
        # }
