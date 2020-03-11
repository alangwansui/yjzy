# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from datetime import datetime
from odoo.exceptions import Warning
from . comm import BACK_TAX_RATIO


class sale_order(models.Model):
    _inherit = 'sale.order'

    # def compute_advance_residual(self):
    #     for one in self:
    #         aml_obj = one.env['account.move.line']
    #         lines = aml_obj.search([('so_id', '=', one.id)]).filtered(lambda x: x.account_id.code == '2203')
    #
    #         one.advance_residual = -1 * sum([
    #             i.get_amount_to_currency(one.currency_id) for i in lines
    #         ])

    @api.depends('currency_id', 'contract_date')
    def compute_exchange_rate(self):
        for one in self:
            date = one.contract_date or fields.date.today()
            currench_obj = self.env['res.currency'].with_context(date=date)
            exchange_rate = 0
            if one.currency_id:
                from_currency = one.currency_id
                to_currency = self.env.user.company_id.currency_id
                exchange_rate = currench_obj._get_conversion_rate(from_currency, to_currency)
            one.exchange_rate = exchange_rate
            one.appoint_rate = exchange_rate

    def default_commission_ratio(self):
        return  float(self.env['ir.config_parameter'].sudo().get_param('addons_yjzy.sale_commission', '0.015'))


    @api.depends('aml_ids')
    def compute_balance(self):
        for one in self:
            sml_lines = one.aml_ids.filtered(lambda x: x.account_id.code == '2203')
            if one.yjzy_payment_ids and one.yjzy_payment_ids[0].currency_id.name == 'CNY':
                balance = sum([x.credit - x.debit for x in sml_lines])
            else:
                balance = sum([-1 * x.amount_currency for x in sml_lines])
            one.balance = balance


    #@api.depends('po_ids.balance')
    def compute_po_residual(self):
        for one in self:
            one.advance_po_residual = sum([x.balance for x in one.po_ids])

    def compute_info(self):
        aml_obj = self.env['account.move.line']
        for one in self:

            one.tb_ids = one.order_line.mapped('tbl_ids').mapped('bill_id')

            print('==', one.order_line.mapped('tbl_ids').mapped('bill_id'), one.order_line.mapped('tbl_ids'), one.order_line)



            one.tb_count = len(one.tb_ids)
            one.no_sent_amount = sum([x.price_unit * (x.product_uom_qty - x.qty_delivered) for x in one.order_line])


            #统计预收余额
            if one.payment_term_id:
                one.pre_advance = one.payment_term_id.get_advance(one.amount_total )

            # sml_lines = aml_obj.search([('so_id', '=', one.id)]).filtered(lambda x: x.account_id.code == '2203')
            #
            # if one.yjzy_payment_ids and one.yjzy_payment_ids[0].currency_id.name == 'CNY':
            #     balance = sum([x.credit - x.debit for x in sml_lines])
            # else:
            #     balance = sum([-1 * x.amount_currency for x in sml_lines])
            #
            # one.balance = balance

            ##金额统计
            lines = one.order_line
            if not lines: continue
            purchase_cost = one.company_currency_id.compute(sum([x.purchase_cost for x in lines]), one.third_currency_id)
            fandian_amoun = one.company_currency_id.compute(sum([x.fandian_amoun for x in lines]), one.third_currency_id)
            stock_cost = one.company_currency_id.compute(sum([x.stock_cost for x in lines]), one.third_currency_id)

            if one.cip_type != 'normal':
                back_tax_amount = 0
            else:
                back_tax_amount = one.company_currency_id.compute(sum(x.back_tax_amount for x in lines), one.third_currency_id)

            other_cost = one._get_other_cost()
            amount_total2 = one._get_sale_amount()
            commission_amount = one.commission_ratio * amount_total2
            vat_diff_amount = 0
            if one.include_tax and one.company_currency_id.name == 'CNY':
                vat_diff_amount = (one.amount_total2 - one.purchase_cost - one.stock_cost) / 1.13 * 0.13

            profit_amount = (amount_total2 - purchase_cost - stock_cost - fandian_amoun - vat_diff_amount - other_cost - commission_amount + back_tax_amount) / 5
            gross_profit =  (amount_total2 - purchase_cost - stock_cost - fandian_amoun + back_tax_amount) / 5

            one.amount_total2 = amount_total2
            one.commission_amount = commission_amount
            one.stock_cost = stock_cost
            one.purchase_cost = purchase_cost
            one.fandian_amoun = fandian_amoun
            one.vat_diff_amount = vat_diff_amount
            one.other_cost = other_cost
            one.back_tax_amount = back_tax_amount
            one.profit_amount = profit_amount
            one.fee_rmb_all = one.fee_inner + one.fee_rmb1 + one.fee_rmb2
            one.fee_outer_all = one.fee_outer + one.fee_export_insurance + one.fee_other

            one.fee_rmb_ratio = one.amount_total  and  one.company_currency_id.compute(one.fee_rmb_all + fandian_amoun + vat_diff_amount, one.currency_id) / one.amount_total
            one.fee_outer_ratio = one.amount_total and  one.other_currency_id.compute(one.fee_outer_all, one.currency_id) / one.amount_total

            one.profit_ratio = amount_total2 and profit_amount / amount_total2  * 100

            one.gross_profit = gross_profit
            one.gorss_profit_ratio = amount_total2 and (gross_profit / amount_total2  * 100)





    #货币设置
    sale_currency_id = fields.Many2one('res.currency', related='currency_id', string=u'交易货币', store=True)
    company_currency_id = fields.Many2one('res.currency', u'公司货币', default=lambda self: self.env.user.company_id.currency_id.id)
    third_currency_id = fields.Many2one('res.currency', u'统计货币', default=lambda self: self.env.user.company_id.currency_id.id)
    other_currency_id = fields.Many2one('res.currency', u'其他国外费用货币', default=lambda self: self.env.ref('base.USD').id)

    contract_code = fields.Char(u'合同编码')
    contract_date = fields.Date(u'签订日期', required=True, default=lambda self: fields.date.today())
    link_man_id = fields.Many2one('res.partner', u'联系人')
    sale_assistant_id = fields.Many2one('res.users', u'业务助理')
    product_manager_id = fields.Many2one('res.users', u'产品经理')

    incoterm_code = fields.Char(u'贸易术语', related='incoterm.code', readonly=True)

    cost_id = fields.Many2one('sale.cost', u'成本单', copy=False)
    #transport_bill_id = fields.Many2one('transport.bill', u'出运单', copy=False)
    is_cip = fields.Boolean(u'报关', default=True)
    cip_type = fields.Selection([('normal', u'正常报关'), ('buy', u'买单报关'), ('none', '不报关')], string=u'报关', default='normal')
    # 其他费用  fee_inner,fee_rmb1,fee_rmb2,fee_outer,fee_export_insurance,fee_other

    fee_inner = fields.Monetary(u'国内运杂费', currency_field='company_currency_id')
    fee_rmb1 = fields.Monetary(u'人民币费用1', currency_field='company_currency_id')
    fee_rmb2 = fields.Monetary(u'人民币费用2', currency_field='company_currency_id')
    fee_rmb_all = fields.Monetary(u'人民币费用合计', currency_field='company_currency_id',  compute=compute_info)
    fee_rmb_ratio = fields.Float(u'人名币费用占销售额比', digits=(2, 4), compute=compute_info)

    fee_outer = fields.Monetary(u'国外运保费', currency_field='other_currency_id')
    outer_currency_id = fields.Many2one('res.currency', u'国外运保费货币', )
    fee_export_insurance = fields.Monetary(u'出口保险费', currency_field='other_currency_id')
    export_insurance_currency_id = fields.Many2one('res.currency', u'出口保险费货币')
    fee_other = fields.Monetary(u'其他外币费用', currency_field='other_currency_id')
    fee_outer_all = fields.Monetary(u'外币费用合计', currency_field='other_currency_id',  compute=compute_info)
    fee_outer_ratio = fields.Float(u'外币费用占销售额比', digits=(2, 4), compute=compute_info)

    pre_advance = fields.Monetary(u'预收金额', currency_field='currency_id', compute=compute_info, store=True)



    advance_account_id = fields.Many2one('account.account', u'预收认领单')
    advance_currency_id = fields.Many2one('res.currency', u'预收币种', related='advance_account_id.currency_id')

    advance_residual = fields.Monetary(u'预收余额', compute=compute_info, currency_field='advance_currency_id')

    advance_po_residual = fields.Float(u'预付余额', compute=compute_po_residual, store=True)

    yjzy_payment_id = fields.Many2one('account.payment', u'预收认领单')
    yjzy_payment_ids = fields.One2many('account.payment', 'so_id', u'预收认领单')
    yjzy_currency_id = fields.Many2one('res.currency', u'预收币种', related='yjzy_payment_ids.currency_id')
    balance = fields.Monetary(u'预收余额', compute=compute_balance, currency_field='yjzy_currency_id', store=True)

    exchange_rate = fields.Float(u'目前汇率', compute=compute_exchange_rate, digits=(2,6))
    appoint_rate = fields.Float(u'使用汇率', digits=(2,6))
    country_id = fields.Many2one('res.country', related='partner_id.country_id', string=u'国别', readonly=True)
    term_description = fields.Html(u'销售条款')
    commission_ratio = fields.Float(u'经营计提比', digits=(2, 4), default=lambda self: self.default_commission_ratio())
    state2 = fields.Selection([('draft', u'草稿'),('to_approve', u'待批准'), ('edit', u'可修改'), ('confirmed', u'待审批'), ('done', u'审批完成')], u'状态', default='draft')
    amount_total2 = fields.Monetary(u'销售金额', currency_field='third_currency_id', compute=compute_info)
    purchase_cost = fields.Monetary(u'采购成本', currency_field='third_currency_id', compute=compute_info)
    fandian_amoun = fields.Monetary(u'返点金额', currency_field='third_currency_id', compute=compute_info)
    stock_cost = fields.Monetary(u'库存成本', currency_field='third_currency_id', compute=compute_info)
    commission_amount = fields.Monetary(u'经营计提金额', currency_field='third_currency_id', compute=compute_info)
    lines_profit_amount = fields.Monetary(u'明细利润计总', currency_field='third_currency_id')
    other_cost = fields.Monetary(u'其他费用总计', currency_field='third_currency_id', compute=compute_info)
    back_tax_amount = fields.Monetary(u'退税金额', currency_field='third_currency_id', compute=compute_info)
    profit_amount = fields.Monetary(u'净利润', currency_field='third_currency_id', compute=compute_info)
    profit_ratio = fields.Float(u'净利润率%', compute=compute_info)

    gross_profit = fields.Monetary(u'毛利', currency_field='third_currency_id', compute=compute_info)
    gorss_profit_ratio = fields.Float(u'毛利率%', compute=compute_info)

    pdt_value_id = fields.Many2one('product.attribute.value', string=u'产品属性', readonly=True, help=u'只是为在SO上搜索属性,不直接记录数据')
    #is_tb_process = fields.Boolean(u'出运单运行中', help='是否有关联的出运单还未结案?')
    tb_ids = fields.Many2many('transport.bill', 'ref_tb_so', 'tb_id', 'so_id', string=u'出运单', compute=compute_info)
    tb_count = fields.Integer('发运单计数', compute=compute_info)
    include_tax = fields.Boolean(u'含税')
    customer_pi = fields.Char(u'客户订单号')
    from_wharf_id = fields.Many2one('stock.wharf', u'目的港POD')
    to_wharf_id = fields.Many2one('stock.wharf', u'目的港POL')
    vat_diff_amount = fields.Monetary(u'增值税差额', currency_field='third_currency_id', compute=compute_info)

    mark_comb_id = fields.Many2one('mark.comb', u'唛头组')

    no_sent_amount = fields.Monetary(u'未发货的金额', compute=compute_info)

    is_editable = fields.Boolean(u'可编辑')

    aml_ids = fields.One2many('account.move.line', 'so_id', u'分录明细', readonly=True)

    second_partner_id = fields.Many2one('res.partner', u'第二客户')


    @api.constrains('contract_code')
    def check_contract_code(self):
        for one in self:
            if self.search_count([('contract_code', '=', one.contract_code)]) > 1:
                raise Warning('合同编码重复')


    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        if 'contract_code' not in default:
            default['contract_code'] = "%s(copy)" % self.contract_code
        return super(sale_order, self).copy(default)


    @api.multi
    def write(self, vals):
        body = '%s' % vals
        self.message_post(body=body, subject='内容修改', message_type='notification')
        return super(sale_order, self).write(vals)



    def unlink(self):
        for one in self:
            if one.state != 'cancel':
                raise Warning(u'只有取消状态允许删除')
        return super(sale_order, self).unlink()

    @api.multi
    def name_get(self):
        ctx = self.env.context
        res = []
        for one in self:
            name = '%s:%s' % (one.contract_code, one.pre_advance)
            res.append((one.id, name))
        return res



    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        res = super(sale_order, self).search(args, offset=offset, limit=limit, order=order, count=count)
        arg_dic = args and dict([(x[0], x[2]) for x in args if isinstance(x, list)]) or {}
        pdt_value = arg_dic.get('pdt_value_id')
        if pdt_value:
            sol_records = self.env['sale.order.line'].search([('product_id.attribute_value_ids', 'like', pdt_value)])
            res |= sol_records.mapped('order_id')
        return res


    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.term_description = self.partner_id.term_description
        self.user_id = self.partner_id.user_id
        self.sale_assistant_id = self.partner_id.assistant_id
        self.product_manager_id =  self.partner_id.product_manager_id
        self.link_man_id = self.partner_id.child_ids and self.partner_id.child_ids[0]

        return super(sale_order, self).onchange_partner_id()

    def open_advance_residual_lines(self):
        self.ensure_one()
        lines = self.env['account.move.line'].search([('so_id', '=', self.id)]).filtered(lambda x: x.account_id.code == '2203')
        return {
            'name': _(u'订单预收分录明细'),
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'account.move.line',
            'type': 'ir.actions.act_window',
            'domain': [('id', '=', [x.id for x in lines])],
            'target': 'new',
        }

    def _get_sale_amount(self):
        amount_total2 = self.currency_id.compute(self.amount_total, self.third_currency_id)
        if self.incoterm_code == 'FOB':
            amount_total2 += self.outer_currency_id.compute(self.fee_outer, self.third_currency_id)
        return amount_total2

    def _get_other_cost(self):
        return sum([ self.company_currency_id.compute(self.fee_inner, self.third_currency_id),
                     self.company_currency_id.compute(self.fee_rmb1, self.third_currency_id),
                     self.company_currency_id.compute(self.fee_rmb2, self.third_currency_id),
                    self.outer_currency_id.compute(self.fee_outer, self.third_currency_id),
                    self.export_insurance_currency_id.compute(self.fee_export_insurance, self.third_currency_id),
                    self.other_currency_id.compute(self.fee_other, self.third_currency_id),
                    ])

    def _get_other_cost_no_rmb(self):
        return sum([ self.outer_currency_id.compute(self.fee_outer, self.third_currency_id),
                    self.export_insurance_currency_id.compute(self.fee_export_insurance, self.third_currency_id),
                    self.other_currency_id.compute(self.fee_other, self.third_currency_id),
                    ])

    def open_view_transport_bill(self):
        self.ensure_one()
        return {
            'name': _(u'成本单'),
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'transport.bill',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', [x.id for x in self.tb_ids])]
        }

    def action_confirm(self):
        '''so auto po confirm'''
        res = super(sale_order, self).action_confirm()
        todo_po = self.po_ids.filtered(lambda x: x.can_confirm_by_so and x.state not in ['purchase', 'done', 'cancel', 'edit'])
        if todo_po:
            todo_po.button_confirm()
        return res

    def action_confirm2(self):
        self.ensure_one()
        self.state2 = 'confirmed'

    def action_done2(self):
        self.ensure_one()
        self.state2 = 'done'

    def _get_sale_commission(self, sale_amount):
        sale_commission_ratio = float(self.env['ir.config_parameter'].sudo().get_param('addons_yjzy.sale_commission', '0.015'))
        return sale_commission_ratio, sale_amount * sale_commission_ratio

    def _check_done(self):
        pass

    def get_appoint_rate(self):
        self.ensure_one()
        self.appoint_rate = self.exchange_rate

    def open_sale_cost(self):
        self.ensure_one()
        view = self.env.ref('yjzy_extend.view_sale_order_cost_form')
        return {
            'name': _(u'成本单'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'views': [(view.id, 'form')],
            'view_id': view.id,
        }

    def check_bom(self):
        self.ensure_one()
        #保证bom完整

    def open_wizard_bom_sale(self):
        self.ensure_one()
        return {
            'name': _(u'套件销售'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'wizard.bom.sale',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
    
    def check_po_allow(self):
        self.ensure_one()
        for po in self.po_ids:
            if not po.can_confirm_by_so:
                raise Warning(u'PO%s 自动跟随审批还未完成' % po.name)
        return True

    def update_back_tax(self):
        self.ensure_one()
        for line in self.order_line:
            line.back_tax = self.cip_type != 'none' and line.product_id.back_tax or 0

        self.compute_info()




class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def _analytic_compute_delivered_quantity(self):
        res = super(sale_order_line, self)._analytic_compute_delivered_quantity()
        for one in self:
            if one.qty_delivered > one.product_uom_qty:
                raise Warning('发货数不能大于订单数量')
        return res

    def get_stock_cost(self):
        #结果返回为公司本币
        stock_cost = 0.0
        for x in self.smline_ids:
            po_currency = x.lot_id.pol_id.currency_id
            stock_cost += po_currency.compute(x.product_uom_qty * x.lot_id.purchase_price, self.company_currency_id)
        return stock_cost

    def get_purchase_cost(self):
        #结果返回为公司本币
        purchase_cost = fandian_amoun = 0.0
        for x in self.dlr_ids:
            po = x.po_id
            purchase_cost += x.purchase_currency_id.compute(x.purchase_amount, self.company_currency_id)
            fd = 0
            if po.need_purchase_fandian:
                fd = purchase_cost * po.purchase_fandian_ratio  / 100
                if self.include_tax:
                    fd =  fd /1.12

            fandian_amoun += fd

        return purchase_cost, fandian_amoun

    def compute_info(self):
        for one in self:
            #统计未发货
            one.qty_undelivered = one.product_uom_qty - one.qty_delivered
            #统计采购
            one.po_ids = one.pol_ids.mapped('order_id')
            one.pol_id = one.pol_ids and one.pol_ids[0] or False
            one.qty_unreceived = sum([x.product_qty - x.qty_received for x in one.pol_ids])
            one.qty_undelivered = one.product_uom_qty - one.qty_delivered
            #计算金额
            price_total2 = one.currency_id.compute(one.price_total, one.company_currency_id)
            purchase_cost, fandian_amoun = one.get_purchase_cost()

            stock_cost = one.get_stock_cost()
            #back_tax = one.order_id.cip_type != 'none' and one.product_id.back_tax or 0

            if one.order_id.cip_type != 'normal':
                back_tax_amount = 0
            else:
                back_tax_amount = (purchase_cost + stock_cost) / BACK_TAX_RATIO * one.back_tax  #固定0.16的税，退回0.05

            one.price_total2 = price_total2
            one.purchase_cost = purchase_cost
            one.fandian_amoun = fandian_amoun
            one.stock_cost = stock_cost
            one.profit_amount = price_total2 - purchase_cost - stock_cost - fandian_amoun
            one.back_tax_amount = back_tax_amount

    #currency_id ==销售货币
    sale_currency_id = fields.Many2one('res.currency', related='currency_id', string=u'交易货币', readonly=True)
    company_currency_id = fields.Many2one('res.currency', related='order_id.company_currency_id', readonly=True)
    third_currency_id = fields.Many2one('res.currency', related='order_id.third_currency_id', readonly=True)
    include_tax = fields.Boolean(related='order_id.include_tax')

    last_sale_price = fields.Float('最后销售价', related='product_id.last_sale_price')
    pol_ids = fields.One2many('purchase.order.line', 'sol_id', u'采购明细', copy=False)
    po_ids = fields.Many2many('purchase.order', string=u'采购订单', compute=compute_info, store=False)
    purchase_qty = fields.Float(u'采购数', compute=compute_info, store=False)
    qty_unreceived = fields.Float(u'未收数', compute=compute_info, store=False)
    qty_undelivered = fields.Float(string=u'未发货', readonly=True, store=False, compute=compute_info)
    back_tax = fields.Float(u'退税率', digits=dp.get_precision('Back Tax'))

    price_total2 = fields.Monetary(u'销售金额', currency_field='company_currency_id', compute=compute_info)  # 'sale_amount': sol.price_total,
    purchase_cost = fields.Monetary(u'采购成本', currency_field='company_currency_id', compute=compute_info)
    fandian_amoun = fields.Monetary(u'返点金额', currency_field='company_currency_id', compute=compute_info)
    stock_cost = fields.Monetary(u'库存成本', currency_field='company_currency_id', compute=compute_info)
    back_tax_amount = fields.Monetary(u'退税金额', currency_field='company_currency_id', compute=compute_info)
    cost_amount = fields.Monetary(u'成本金额', currency_field='company_currency_id', compute=compute_info)
    profit_amount = fields.Monetary(u'利润', currency_field='company_currency_id', compute=compute_info)
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    bom_qty = fields.Float(u'BOM数量')
    need_split_bom = fields.Boolean(u'需要展开BOM')
    need_print = fields.Boolean('是否打印', defualt=True)

    s_uom_id = fields.Many2one('product.uom', u'销售打印单位',)
    p_uom_id = fields.Many2one('product.uom', u'采购打印单位',)
    tbl_ids = fields.One2many('transport.bill.line', 'sol_id', u'出运明细')

    second_unit_price = fields.Float('第二价格')
    second_price_total = fields.Monetary(compute='_compute_second', string='第二小计', readonly=True, store=True)

    @api.depends('second_unit_price', 'discount', 'price_unit', 'tax_id')
    def _compute_second(self):
        """
        """
        for line in self:
            price = line.second_unit_price    #* (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'second_price_total': taxes['total_excluded'],
            })


    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
        res = super(sale_order_line, self).product_id_change()
        self.back_tax = self.product_id.back_tax
        self.s_uom_id = self.product_id.uom_id
        self.p_uom_id = self.product_id.uom_po_id
        self.need_split_bom = self.product_id.need_split_bom
        self.need_print = self.product_id.need_print
        return res

    def _prepare_invoice_line(self, qty):
        u'''开票数量根据发运单指定'''
        ctx = self.env.context
        manual_qty_dic = ctx.get('manual_qty_dic', {})
        if manual_qty_dic.get(self.id):
            manual_qty = manual_qty_dic.get(self.id)
            if manual_qty > qty:
                raise Warning(u'手动开票数量已经超过剩余开票数量')
            else:
                qty = manual_qty
        return super(sale_order_line, self)._prepare_invoice_line(qty)

    def get_in_stock_quant(self):
        self.ensure_one()
        return self.product_id.get_in_stock_quant()


    def show_product_attrs(self):
        values = self.product_id.attribute_value_ids
        return {
            'type': 'ir.actions.act_window',
            'name': u'产品属性',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'product.attribute.value',
            'domain': [('id', 'in', [x.id for x in values])],
            'target': 'new',
        }

