# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from . comm import BACK_TAX_RATIO

class sale_cost(models.Model):
    _name = 'sale.cost'
    _rec_name = 'so_id'
    _description = u'原始成本单'

    @api.model
    def _get_company(self):
        return self._context.get('company_id', self.env.user.company_id.id)

    name = fields.Char(u'Name')
    date = fields.Date(u'确认日期', default=lambda self: fields.date.today())
    state = fields.Selection([('draft', u'草稿'), ('confirmed', u'待审批'), ('done', u'审批完成')], u'状态', default='draft')
    company_id = fields.Many2one('res.company', u'公司', required=True, readonly=True, default=lambda self: self._get_company())
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True, string='货币')

    so_id = fields.Many2one('sale.order', u'销售订单')
    contract_code = fields.Char(u'合同编码', related='so_id.contract_code')
    contract_date = fields.Date(u'签订日期', related='so_id.contract_date')

    is_cip = fields.Boolean(related='so_id.is_cip', readonly=True)
    cip_type = fields.Selection(related='so_id.cip_type')


    incoterm_code = fields.Char(u'贸易术语', related='so_id.incoterm.code', readonly=True)

    sale_user_id = fields.Many2one('res.users', u'客户经理', related='so_id.user_id', readonly=True)
    sale_assistant_id = fields.Many2one('res.users', u'业务助理', related='so_id.sale_assistant_id', readonly=True)
    product_manager_id = fields.Many2one('res.users', u'产品经理', related='so_id.product_manager_id', readonly=True)

    sale_amount = fields.Float(u'销售金额', currency_field='currency_id')
    purchase_cost = fields.Float(u'采购成本')
    stock_cost = fields.Float(u'库存成本')
    sale_commission_ratio = fields.Float(u'经营计提比', digits=(2, 4))
    sale_commission_amount = fields.Float(u'经营计提金额', currency_field='currency_id')
    lines_profit_amount = fields.Float(u'明细利润计总')
    other_cost = fields.Float(u'其他费用总计')
    back_tax_amount = fields.Float(u'退税金额')
    profit_amount = fields.Float(u'利润')

    line_ids = fields.One2many('sale.cost.line', 'cost_id', u'明细')

    # 其他费用  fee_inner,fee_rmb1,fee_rmb2,fee_outer,fee_export_insurance,fee_other
    company_currency_id = fields.Many2one(related='so_id.company_currency_id', readonly=True)
    fee_inner = fields.Monetary(related='so_id.fee_inner', readonly=True)
    fee_rmb1 = fields.Monetary(related='so_id.fee_rmb1', readonly=True)
    fee_rmb2 = fields.Monetary(related='so_id.fee_rmb2', readonly=True)
    fee_outer = fields.Monetary(related='so_id.fee_outer', readonly=True)
    outer_currency_id = fields.Many2one('res.currency',related='so_id.outer_currency_id', readonly=True)
    fee_export_insurance = fields.Monetary(related='so_id.fee_export_insurance', readonly=True)
    export_insurance_currency_id = fields.Many2one('res.currency', related='so_id.export_insurance_currency_id', readonly=True)
    fee_other = fields.Monetary(related='so_id.fee_other', readonly=True)
    other_currency_id = fields.Many2one('res.currency',related='so_id.other_currency_id', readonly=True)
    #wkf_state = fields.Selection(related='so_id.x_wkf_state', string=u'销售审批状态')
    appoint_rate = fields.Float(u'使用汇率')

    def unlink(self):
        for one in self:
            if one.state != 'draft':
                raise Warning(u'不能删除非草稿成本单据')

    def _get_sale_amount(self):
        sale_amount = self.so_id.currency_id.compute(self.so_id.amount_total, self.currency_id)
        if self.incoterm_code == 'FOB':
            sale_amount += self.outer_currency_id.compute(self.fee_outer, self.currency_id)
        return sale_amount

    def _get_other_cost(self):
        return sum([self.fee_inner, self.fee_rmb1, self.fee_rmb2,
                    self.outer_currency_id.compute(self.fee_outer, self.currency_id),
                    self.export_insurance_currency_id.compute(self.fee_export_insurance, self.currency_id),
                    self.other_currency_id.compute(self.fee_other, self.currency_id),
                    ])

    def _get_sale_commission(self, sale_amount):
        sale_commission_ratio = float(self.env['ir.config_parameter'].sudo().get_param('addons_yjzy.sale_commission', '0.015'))
        return sale_commission_ratio, sale_amount * sale_commission_ratio

    def compute_cost(self):
        self.ensure_one()

        lines = self.line_ids
        lines.compute_cost(cip_type=self.cip_type)

        purchase_cost = sum([x.purchase_cost for x in lines])
        stock_cost = sum([x.stock_cost for x in lines])
        back_tax_amount = sum(x.back_tax_amount for x in lines)
        #fee_outer = self.outer_currency_id.compute(self.fee_outer, self.currency_id)
        other_cost = self._get_other_cost()
        sale_amount = self._get_sale_amount()
        sale_commission_ratio, sale_commission_amount = self._get_sale_commission(sale_amount)
        profit_amount = sale_amount - purchase_cost - stock_cost - other_cost - sale_commission_amount + back_tax_amount

        self.write({
            'sale_amount': sale_amount,
            'sale_commission_ratio': sale_commission_ratio,
            'sale_commission_amount': sale_commission_amount,
            'stock_cost': stock_cost,
            'purchase_cost': purchase_cost,
            'other_cost': other_cost,
            'back_tax_amount':back_tax_amount,
            'profit_amount': profit_amount
        })

        # self.sale_amount = sale_amount
        # self.sale_commission_ratio = sale_commission_ratio
        # self.other_cost = other_cost
        # self.sale_commission_amount = sale_commission_amount
        # self.profit_amount = sale_amount - purchase_cost - stock_cost - other_cost - sale_commission_amount


class sale_cost_line(models.Model):
    _name = 'sale.cost.line'
    _description = u'原始成本单明细'

    cost_id = fields.Many2one('sale.cost', u'成本单')
    currency_id = fields.Many2one('res.currency', related='cost_id.currency_id', readonly=True)
    name = fields.Char(u'说明')
    sol_id = fields.Many2one('sale.order.line', u'销售明细')
    product_id = fields.Many2one('product.product', related='sol_id.product_id', string=u'产品')
    sale_qty = fields.Float(u'销售数', related='sol_id.product_uom_qty')

    smline_ids = fields.One2many('stock.move.line', related='sol_id.smline_ids', string=u'库存预留')
    smline_str = fields.Char(related='sol_id.smline_str', string=u'锁定内容')
    smline_qty = fields.Float(related='sol_id.smline_qty', string=u'锁定总数')
    dlr_ids = fields.One2many('dummy.lot.reserve', related='sol_id.dlr_ids', string=u'采购预留')
    dlr_str = fields.Char(related='sol_id.dlr_str', string=u'采购预留')
    dlr_qty = fields.Float(related='sol_id.dlr_qty', string=u'采购预留数')

    back_tax = fields.Float(u'退税率%', digits=dp.get_precision('Back Tax'))
    sale_amount = fields.Monetary(u'销售金额', currency_field='currency_id')  # 'sale_amount': sol.price_total,
    sale_currency_id = fields.Many2one('res.currency', related='sol_id.currency_id', readonly=True, string='销售货币')
    org_currency_sale_amount = fields.Monetary(u'销售货币金额', related='sol_id.price_total', readonly=True,)
    cost_amount = fields.Float(u'成本金额')
    profit_amount = fields.Float(u'利润')

    purchase_cost = fields.Float(u'采购成本')
    stock_cost = fields.Float(u'库存成本')
    back_tax_amount = fields.Float(u'退税金额')

    @api.multi
    def compute_cost(self, cip_type='normal'):
        for one in self:
            sale_amount = one.sol_id.currency_id.compute(one.sol_id.price_total, one.currency_id)
            purchase_cost = sum([x.qty * x.lot_id.purchase_price for x in one.dlr_ids])  #.filtered(lambda x: x.state == 'draft')
            stock_cost = sum([x.product_uom_qty * x.lot_id.purchase_price  for x in one.smline_ids])
            back_tax = cip_type == 'normal' and one.product_id.back_tax or 0
            back_tax_amount = (purchase_cost + stock_cost) / BACK_TAX_RATIO * back_tax  #固定0.16的税，退回0.05

            one.back_tax = back_tax
            one.sale_amount = sale_amount
            one.purchase_cost = purchase_cost

            one.stock_cost = stock_cost
            one.profit_amount = sale_amount - purchase_cost - stock_cost
            one.back_tax_amount = back_tax_amount



class wizad_purchase_cost_detail(models.Model):
    _name = 'wizard.purchase.cost.detail'

    scl_id = fields.Many2one('sale.cost.line')
    sol_id = fields.Many2one('sale.order.line', related='scl_id.sol_id', string=u'销售明细')



class cost_supplier(models.Model):
    _name = 'cost.supplier'
    _description = u'供应商成本汇总'

    cost_id = fields.Many2one('sale.cost', u'成本单')
    supplier_id = fields.Many2one('res.partner', domain=[('supplier', '=', True)])
    amount = fields.Float('金额')
