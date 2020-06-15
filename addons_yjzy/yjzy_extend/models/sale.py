# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from datetime import datetime
from odoo.exceptions import Warning
from . comm import BACK_TAX_RATIO
from dateutil.relativedelta import relativedelta


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
    def compute_balance_new(self):
        for one in self:
            if one.state != 'verification':
                sml_lines = one.aml_ids.filtered(lambda x: x.account_id.code == '2203')
                if one.yjzy_payment_ids and one.yjzy_payment_ids[0].currency_id.name == 'CNY':
                    balance = sum([x.credit - x.debit for x in sml_lines])
                else:
                    balance = sum([-1 * x.amount_currency for x in sml_lines])
                one.balance_new = balance


    def compute_balance(self):
        for one in self:
            sml_lines = one.aml_ids.filtered(lambda x: x.account_id.code == '2203')
            if one.yjzy_payment_ids and one.yjzy_payment_ids[0].currency_id.name == 'CNY':
                balance = sum([x.credit - x.debit for x in sml_lines])
            else:
                balance = sum([-1 * x.amount_currency for x in sml_lines])
            one.balance = balance
   # @api.depends('po_ids')
    def compute_purchase_balance(self):
        for one in self:
             purchase_balance_sum = sum(one.po_ids.mapped('balance'))
             one.purchase_balance_sum = purchase_balance_sum
    @api.one
    @api.depends('po_ids_new.balance_new')
    def compute_purchase_balance3(self):
        for one in self:
            if one.state != 'verification':
                print('balance_new', one)
                purchase_balance_sum = sum(one.po_ids_new.mapped('balance_new'))
                one.purchase_balance_sum3 = purchase_balance_sum



    def compute_purchase_amount_total(self):
        for one in self:
            print('total', one)
            purchase_amount_total = sum(one.po_ids_new.mapped('amount_total'))
            one.purchase_amount_total = purchase_amount_total

    @api.one
    @api.depends('po_ids_new.amount_total')
    def compute_purchase_amount_total_new(self):
        for one in self:
            if one.state != 'verification':
                print('total', one)
                purchase_amount_total = sum(one.po_ids_new.mapped('amount_total'))
                one.purchase_amount_total_new = purchase_amount_total



    @api.depends('order_line.qty_delivered')
    def compute_no_sent_amount(self):
        for one in self:
            if one.state != 'verification':
                one.no_sent_amount_new = sum([x.price_unit * (x.product_uom_qty - x.qty_delivered) for x in one.order_line])



    @api.one
    @api.depends('po_ids_new.no_deliver_amount_new')
    def compute_purchase_no_deliver_amount_new(self):
        for one in self:
            if one.state != 'verification':
                print('total', one)
                one.purchase_no_deliver_amount_new = sum(one.po_ids_new.mapped('no_deliver_amount_new'))




    #@api.depends('po_ids.balance')
    def compute_po_residual(self):
        for one in self:
            one.advance_po_residual = sum([x.balance for x in one.po_ids])

    def compute_info(self):
        aml_obj = self.env['account.move.line']
        for one in self:
            one.tb_ids = one.order_line.mapped('tbl_ids').mapped('bill_id')
            one.tb_count = len(one.tb_ids)
            one.no_sent_amount = sum([x.price_unit * (x.product_uom_qty - x.qty_delivered) for x in one.order_line])

            #统计预收余额
            if one.payment_term_id:
                one.pre_advance = one.payment_term_id.get_advance(one.amount_total)

                print('====', one, one.pre_advance)

            ##金额统计
            lines = one.order_line
            if not lines: continue
            purchase_cost = one.company_currency_id.compute(sum([x.purchase_cost for x in lines]), one.third_currency_id)
            fandian_amoun = one.company_currency_id.compute(sum([x.fandian_amoun for x in lines]), one.third_currency_id)
            stock_cost = one.company_currency_id.compute(sum([x.stock_cost for x in lines]), one.third_currency_id)

            #样金计算
            gold_sample_state = 'none'
            line_count = len(one.order_line)
            line_count_gold = len(one.order_line.filtered(lambda x: x.is_gold_sample))

            if line_count_gold > 0:
                if line_count_gold == line_count:
                    gold_sample_state = 'all'
                else:
                    gold_sample_state = 'part'

            if one.cip_type != 'normal':
                back_tax_amount = 0
            else:
                back_tax_amount = one.company_currency_id.compute(sum(x.back_tax_amount for x in lines), one.third_currency_id)

            amount_total2 = one._get_sale_amount()
          #  amount_total3 = one._get_amount_total3()
            commission_amount = one.commission_ratio * amount_total2

          #  commission_amount2 = one.commission_ratio * amount_total3

            other_cost = one._get_other_cost()


            vat_diff_amount = 0
            if one.include_tax and one.company_currency_id.name == 'CNY':
                vat_diff_amount = (one.amount_total2 - one.purchase_cost - one.stock_cost) / 1.13 * 0.13

            expense_cost_total = other_cost + commission_amount + vat_diff_amount

            profit_amount = (amount_total2 - purchase_cost - stock_cost - fandian_amoun - vat_diff_amount - other_cost - commission_amount + back_tax_amount) / 5
            gross_profit = (amount_total2 - purchase_cost - stock_cost - fandian_amoun + back_tax_amount) / 5



            purchase_no_deliver_amount = sum(one.po_ids.mapped('no_deliver_amount'))





            purchase_approve_date = False
            for po in one.po_ids:
                if po.purchaser_date:
                    if not purchase_approve_date:
                        purchase_approve_date = po.purchaser_date
                    else:
                        pass
                else:
                    pass


            one.amount_total2 = amount_total2
            one.commission_amount = commission_amount
            one.stock_cost = stock_cost
            one.purchase_cost = purchase_cost
            one.purchase_stock_cost = purchase_cost + stock_cost
            one.fandian_amoun = fandian_amoun
            one.vat_diff_amount = vat_diff_amount
            one.other_cost = other_cost
            one.back_tax_amount = back_tax_amount
            one.profit_amount = profit_amount
            one.fee_rmb_all = one.fee_inner + one.fee_rmb1 + one.fee_rmb2
            one.fee_outer_all = one.fee_outer + one.fee_export_insurance + one.fee_other

            #one.fee_rmb_ratio = one.amount_total and one.company_currency_id.compute(one.fee_rmb_all + fandian_amoun + vat_diff_amount, one.currency_id) / one.amount_total * 100
            #akiny 用新的汇率计算
            one.fee_rmb_ratio = one.amount_total2 and (
                        one.fee_rmb_all + fandian_amoun + vat_diff_amount) / one.amount_total2 * 100
            one.fee_outer_ratio = one.amount_total and one.other_currency_id.compute(one.fee_outer_all, one.currency_id) / one.amount_total *100



            one.fee_all_ratio = amount_total2 and expense_cost_total / one.amount_total2 *100

            one.profit_ratio = amount_total2 and profit_amount / amount_total2 * 100

            one.gross_profit = gross_profit
            one.gorss_profit_ratio = amount_total2 and (gross_profit / amount_total2 * 100)
            one.gold_sample_state = gold_sample_state
            one.purchase_no_deliver_amount = purchase_no_deliver_amount
            one.purchase_approve_date = purchase_approve_date
            one.second_cost = sum(one.order_line.mapped('second_price_total'))
            one.second_porfit = one.amount_total2 - one.second_cost
            one.second_tenyale_profit = one.company_currency_id.compute(one.second_cost, one.third_currency_id) - one.purchase_cost - one.stock_cost
            one.commission_ratio_percent = one.commission_ratio * 100
            one.expense_cost_total = expense_cost_total



    #货币设置


    company_currency_id = fields.Many2one('res.currency', u'公司货币', default=lambda self: self.env.user.company_id.currency_id.id)

    other_currency_id = fields.Many2one('res.currency', u'其他国外费用货币', default=lambda self: self.env.ref('base.USD').id)
    third_currency_id = fields.Many2one('res.currency', u'统计货币',
                                        default=lambda self: self.env.user.company_id.currency_id.id)
    #不需要
    third_currency_id = fields.Many2one('res.currency', u'统计货币',
                                        default=lambda self: self.env.user.company_id.currency_id.id)
    sale_currency_id = fields.Many2one('res.currency', related='currency_id', string=u'交易货币', store=True)
    product_manager_id = fields.Many2one('res.users', u'产品经理')
    incoterm_code = fields.Char(u'贸易术语', related='incoterm.code', readonly=True)
    cost_id = fields.Many2one('sale.cost', u'成本单', copy=False)
    fee_rmb2_note = fields.Text(u'人名币备注2')
    fee_rmb1_note = fields.Text(u'人名币备注1')
    fee_other_note = fields.Text(u'外币备注1')
    advance_account_id = fields.Many2one('account.account', u'预收认领单')
    advance_currency_id = fields.Many2one('res.currency', u'预收币种', related='advance_account_id.currency_id')
    yjzy_payment_id = fields.Many2one('account.payment', u'预收认领单')
    advance_residual = fields.Monetary(u'预收余额', compute=compute_info, currency_field='advance_currency_id')
    is_inner_trade = fields.Boolean('内部交易')
    second_company_id = fields.Many2one('res.company', '内部交易公司')
    country_id = fields.Many2one('res.country', related='partner_id.country_id', readonly=True, string=u'国家')
    second_partner_id = fields.Many2one('res.partner', u'第二客户')
    order_line_b = fields.One2many('sale.order.line', related='order_line')
    po_ids_term = fields.Many2many('purchase.order', '采购合同条款', related='po_ids')
    #。。。。。
    contract_code = fields.Char(u'合同编码')
    contract_date = fields.Date(u'签订日期')
    link_man_id = fields.Many2one('res.partner', u'联系人')
    sale_assistant_id = fields.Many2one('res.users', u'业务助理')



    #transport_bill_id = fields.Many2one('transport.bill', u'出运单', copy=False)
    is_cip = fields.Boolean(u'报关', default=True)
    cip_type = fields.Selection([('normal', u'正常报关'), ('buy', u'买单报关'), ('none', '不报关')], string=u'报关', default='normal')
    # 其他费用  fee_inner,fee_rmb1,fee_rmb2,fee_outer,fee_export_insurance,fee_other

    fee_inner = fields.Monetary(u'国内运杂费', currency_field='company_currency_id')
    fee_rmb1 = fields.Monetary(u'人民币费用1', currency_field='company_currency_id')

    fee_rmb2 = fields.Monetary(u'人民币费用2', currency_field='company_currency_id')

    fee_rmb_all = fields.Monetary(u'人民币费用合计', currency_field='company_currency_id',  compute=compute_info)
    fee_rmb_ratio = fields.Float(u'人名币费用占销售额比', digits=(2, 2), compute=compute_info) #akiny 4改成了2

    fee_outer = fields.Monetary(u'国外运保费', currency_field='other_currency_id')
    outer_currency_id = fields.Many2one('res.currency', u'国外运保费货币', )
    fee_export_insurance = fields.Monetary(u'出口保险费', currency_field='other_currency_id')
    export_insurance_currency_id = fields.Many2one('res.currency', u'出口保险费货币')
    fee_other = fields.Monetary(u'其他外币费用', currency_field='other_currency_id')


    fee_outer_all = fields.Monetary(u'外币费用合计', currency_field='other_currency_id',  compute=compute_info)
    fee_outer_ratio = fields.Float(u'外币费用占销售额比', digits=(2, 2), compute=compute_info) #akiny 4改成了2

    fee_all_ratio = fields.Float(u'总费用占比', digits=(2, 2), compute=compute_info)#akiny 4改成了2

    pre_advance = fields.Monetary(u'预收金额', currency_field='currency_id', compute=compute_info, store=False)







    advance_po_residual = fields.Float(u'预付余额', compute=compute_po_residual, store=True)


    yjzy_payment_ids = fields.One2many('account.payment', 'so_id', u'预收认领单')
    yjzy_currency_id = fields.Many2one('res.currency', u'预收币种', related='yjzy_payment_ids.currency_id')
    balance = fields.Monetary(u'预收余额', compute=compute_balance, currency_field='yjzy_currency_id')
    balance_new = fields.Monetary(u'预收余额', compute=compute_balance_new, currency_field='yjzy_currency_id', store=True)

    exchange_rate = fields.Float(u'目前汇率', compute=compute_exchange_rate, digits=(2,2)) #akiny 4改成了2
    appoint_rate = fields.Float(u'使用汇率', digits=(2,6))
    #currency_tate = fields.Many2one('res.currency.rate',u'系统汇率')
    country_id = fields.Many2one('res.country', related='partner_id.country_id', string=u'国别', readonly=True)
    term_description = fields.Html(u'销售条款')
    commission_ratio = fields.Float(u'经营计提比', digits=(2, 4), default=lambda self: self.default_commission_ratio())
    commission_ratio_percent = fields.Float(u'经营计提比%',compute=compute_info)
    state2 = fields.Selection([('draft', u'草稿'),('to_approve', u'待批准'), ('edit', u'可修改'), ('confirmed', u'待审批'), ('done', u'审批完成')], u'状态', default='draft')
    amount_total2 = fields.Monetary(u'销售金额', currency_field='third_currency_id', compute=compute_info)
    #akiny 手动汇率
   # amount_total3 = fields.Monetary(u'销售金额', currency_field='third_currency_id', compute=compute_info)

    purchase_cost = fields.Monetary(u'采购成本', currency_field='third_currency_id', compute=compute_info)
    purchase_stock_cost = fields.Monetary(u'采购库存成本合计',  currency_field='third_currency_id', compute=compute_info)
    fandian_amoun = fields.Monetary(u'返点金额', currency_field='third_currency_id', compute=compute_info)
    stock_cost = fields.Monetary(u'库存成本', currency_field='third_currency_id', compute=compute_info)
    commission_amount = fields.Monetary(u'经营计提金额', currency_field='third_currency_id', compute=compute_info)
    lines_profit_amount = fields.Monetary(u'明细利润计总', currency_field='third_currency_id')
    other_cost = fields.Monetary(u'其他费用总计', currency_field='third_currency_id', compute=compute_info)

    expense_cost_total = fields.Monetary(u'所有费用总和',currency_field='third_currency_id',compute=compute_info)

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
    mark_text = fields.Text(u'唛头')

    no_sent_amount = fields.Monetary(u'未发货的金额', compute=compute_info)
    no_sent_amount_new = fields.Monetary(u'未发货的金额', compute=compute_no_sent_amount, store=True)
    is_editable = fields.Boolean(u'可编辑')
    display_detail = fields.Boolean(u'显示详情')
    aml_ids = fields.One2many('account.move.line', 'so_id', u'分录明细', readonly=True)


    gold_sample_state = fields.Selection([('all', '全部有'), ('part', '部分有'), ('none', '无金样')], '样金管理', compute=compute_info)





    partner_payment_term_id = fields.Many2one('account.payment.term',u'客户付款条款', related='partner_id.property_payment_term_id')

    current_date_rate = fields.Float('当日汇率')

    contract_type = fields.Selection([('a', '模式1'), ('b', '模式2'), ('c', '模式3')], '合同类型', default='c')


    gongsi_id = fields.Many2one('gongsi', '内部公司')
    purchase_gongsi_id = fields.Many2one('gongsi', '内部采购公司')


    approvaled_date = fields.Datetime('审批完成时间')

    # akiny 增加state
    #state = fields.Selection(selection_add=[('refuse', u'拒绝'), ('submit', u'已提交'),('sales_approve', u'责任人已审批'),
                                       #     ('approve', u'审批完成'), ('manager_approval', u'待总经理审批'),
                                       #     ('verifying', u'核销中'), ('verification', u'核销完成')],readonly=False)
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('check',u'检查'),
        ('submit', u'待责任人审核'),
        ('sales_approve', u'待业务合规审核'),
        ('manager_approval', u'待总经理特批'),
        ('approve', u'审批完成待出运'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ('refuse', u'拒绝'),
        ('verifying', u'待核销'),
        ('verification', u'核销完成'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')

    submit_date = fields.Date('提交审批时间')
    submit_uid = fields.Many2one('res.users', u'提交审批')
    sales_confirm_date = fields.Date('责任人审批时间')
    sales_confirm_uid = fields.Many2one('res.users', u'责任人审批')
    approve_date = fields.Date('审批完成日期')
    approve_uid = fields.Many2one('res.users', u'完成审批人')

    hegui_date = fields.Date('合规审批日期')
    hegui_uid = fields.Many2one('res.users', u'合规审批')


    hx_date = fields.Date('核销时间')
    purchase_approve_date = fields.Datetime('采购审批时间', compute=compute_info)

    purchase_no_deliver_amount = fields.Float('未发货的采购金额', compute=compute_info)
    purchase_no_deliver_amount_new = fields.Float('未发货的采购金额', compute='compute_purchase_no_deliver_amount_new',store=True)
    purchase_delivery_status = fields.Boolean('采购发货完成', compute='update_purchase_delivery')
    purchase_balance_sum = fields.Float('采购预付余额',compute='compute_purchase_balance')
    purchase_balance_sum3 = fields.Float('采购预付余额',compute='compute_purchase_balance3',store=True)
    # purchase_balance_sum2 = fields.Float('采购预付余额',compute='compute_purchase_balance2',store=True)
    purchase_amount_total_new = fields.Float('采购金额',compute='compute_purchase_amount_total_new',store=True)
    purchase_amount_total = fields.Float('采购金额', compute='compute_purchase_amount_total')

    second_cost = fields.Float('销售主体成本', compute=compute_info)   #second_amoun
    second_porfit = fields.Float('销售主体利润', compute=compute_info) #amount_total2-刚刚计算出来的 second_const
    second_tenyale_profit = fields.Float('采购主体利润', compute=compute_info)#(采购主体利润)：

    is_different_payment_term = fields.Boolean('付款条款是否不同')

    hexiao_type = fields.Selection([('abnormal',u'异常核销'),('write_off',u'正常核销')], string='核销类型')

    hexiao_comment = fields.Text(u'异常核销备注')
    doing_type = fields.Selection([('undelivered', u'未发货'), ('start_delivery', u'开始发货'),
                                   ('wait_hexiao',u'待核销'),('has_hexiao',u'已核销')],
                                   u'出运与核销状态')
    # purchase_update_date = fields.Datetime(u'采购更新的时间')

    po_ids_new = fields.One2many('purchase.order','source_so_id','采购合同新')

    # : 公式的cost改成second_cost
    # second_tenyale_profit：原公式的销售额改成second_cost
    # second_unit_price: = 订单
   # 手动计算采购单balance
    def compute_purchase_balance4(self):
        print('---',self)
        purchase_balance_sum = sum(self.po_ids.mapped('balance_new'))
        self.purchase_balance_sum4 = purchase_balance_sum


    @api.constrains('current_date_rate','fee_inner')
    def check_fields(self):
        if self.current_date_rate <= 0:
            raise Warning(u'汇率必须大于0')


    @api.onchange('payment_term_id')
    def onchange_payment_term_id(self):

        if self.payment_term_id != self.partner_payment_term_id:
            self.is_different_payment_term = True
        else:
            self.is_different_payment_term = False

    @api.onchange('contract_type')
    def onchange_contract_type(self):
        gongsi_obj = self.env['gongsi']
        if self.contract_type == 'b':
            self.is_inner_trade = True
            self.gongsi_id = gongsi_obj.search([('name','=','BERTZ')], limit=1)
            self.purchase_gongsi_id = gongsi_obj.search([('name', '=', '天宇进出口')], limit=1)

        else:
            self.is_inner_trade = False


    @api.onchange('second_company_id')
    def onchange_second_company(self):
        self.second_partner_id = self.second_company_id.partner_id


    @api.constrains('contract_code')
    def check_contract_code(self):
        for one in self:
            if self.search_count([('contract_code', '=', one.contract_code)]) > 1:
                raise Warning('合同编码重复')


    @api.multi
    def copy(self, default=None):
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

    def name_get(self):
        res = []
        for order in self:
            name = '%s' % (order.contract_code)
            res.append((order.id, name))
        return res
    # @api.multi
    # def name_get(self):
    #     ctx = self.env.context
    #     res = []
    #     for one in self:
    #         name = '%s:%s' % (one.contract_code, one.pre_advance)
    #         res.append((one.id, name))
    #     return res



    # @api.model
    # def search(self, args, offset=0, limit=None, order=None, count=False):
    #     res = super(sale_order, self).search(args, offset=offset, limit=limit, order=order, count=count)
    #     arg_dic = args and dict([(x[0], x[2]) for x in args if isinstance(x, list)]) or {}
    #     pdt_value = arg_dic.get('pdt_value_id')
    #     if pdt_value:
    #         sol_records = self.env['sale.order.line'].search([('product_id.attribute_value_ids', 'like', pdt_value)])
    #         res |= sol_records.mapped('order_id')
    #     return res


    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.term_description = self.partner_id.term_description
        self.user_id = self.partner_id.user_id
        self.sale_assistant_id = self.partner_id.assistant_id
        self.product_manager_id =  self.partner_id.product_manager_id
        self.contract_type = self.partner_id.contract_type
        self.gongsi_id = self.partner_id.gongsi_id
        self.purchase_gongsi_id = self.partner_id.purchase_gongsi_id
        self.link_man_id = self.partner_id.child_ids and self.partner_id.child_ids[0]
        self.mark_text = self.partner.shipping_id.mark_text
        self.from_wharf_id = self.partner.shipping_id.from_wharf_id
        self.to_wharf_id = self.partner.shipping_id.to_wharf_id


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
#akiny 加入对是否使用今日手填汇率的判断
    def _get_sale_amount(self):
        if self.company_id.is_current_date_rate:
            amount_total2 = self.amount_total * self.current_date_rate
            if self.incoterm_code == 'FOB':
                amount_total2 += self.fee_outer * self.current_date_rate
        else:
            amount_total2 = self.currency_id.compute(self.amount_total, self.third_currency_id)
            if self.incoterm_code == 'FOB':
                amount_total2 += self.outer_currency_id.compute(self.fee_outer, self.third_currency_id)


        return amount_total2

   # def _get_amount_total3(self):
   #     current_date_rate = self.current_date_rate
   #     amount_total3 = self.amount_total * current_date_rate
   #     if self.incoterm_code == 'FOB':
   #         amount_total3 += sself.fee_outer * self.current_date_rate
   #     return amount_total3

    # akiny 加入对是否使用今日手填汇率的判断
    def _get_other_cost(self):
        if self.company_id.is_current_date_rate:
            other_cost = (self.fee_outer + self.fee_export_insurance + self.fee_other) * self.current_date_rate + self.fee_inner + self.fee_rmb1 +self.fee_rmb2
            return other_cost

        else:
           return sum([ self.company_currency_id.compute(self.fee_inner, self.third_currency_id),
                     self.company_currency_id.compute(self.fee_rmb1, self.third_currency_id),
                     self.company_currency_id.compute(self.fee_rmb2, self.third_currency_id),
                    self.outer_currency_id.compute(self.fee_outer, self.third_currency_id),
                    self.export_insurance_currency_id.compute(self.fee_export_insurance, self.third_currency_id),
                    self.other_currency_id.compute(self.fee_other, self.third_currency_id),
                    ])

    # akiny 加入对是否使用今日手填汇率的判断
    def _get_other_cost_no_rmb(self):
        if self.company_id.is_current_date_rate:
            other_cost_no_rmb = (self.fee_outer + self.fee_export_insurance + self.fee_other)*self.current_date_rate
            return other_cost_no_rmb
        else:
            return sum([ self.outer_currency_id.compute(self.fee_outer, self.third_currency_id),
                    self.export_insurance_currency_id.compute(self.fee_export_insurance, self.third_currency_id),
                    self.other_currency_id.compute(self.fee_other, self.third_currency_id),
                    ])

    def open_view_transport_bill(self):
        self.ensure_one()
        tree_view = self.env.ref('yjzy_extend.view_transport_bill_new_sales_tree')
        form_view = self.env.ref('yjzy_extend.view_transport_bill_new_sales_form')
        return {
            'name': _(u'成本单'),
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'transport.bill',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('id', 'in', [x.id for x in self.tb_ids])]
        }

    def action_confirm(self):
        '''so auto po confirm'''
        res = super(sale_order, self).action_confirm()
        #akiny to approve的时候触发button_approve
       # todo_po = self.po_ids.filtered(lambda x: x.can_confirm_by_so and x.state not in ['purchase', 'done', 'cancel', 'edit'])
        todo_po1 = self.po_ids.filtered(lambda x: x.can_confirm_by_so and x.state in ['to approve'])
      #  if todo_po:
      #      todo_po.button_confirm()
        if todo_po1:
            todo_po1.button_approve()
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


    @api.model
    def cron_update_rate(self):
        print('=cron_update_rate==')
        currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
        for one in self.search(['|', ('current_date_rate', '=', 0),('current_date_rate', '=', False)]):
            print('===', one)
            if one.contract_date:
                rate = currency.with_context(date=one.contract_date).rate
                if rate != 0:
                    one.current_date_rate = 1 / rate

    @api.model
    def cron_update_contract_type(self):
        print('=cron_update_rate==')

        for one in self:
            print('===', one)
            one.contract_type = one.partner_id.contract_type
            one.gongsi_id = one.partner_id.gongsi_id
            one.purchase_gongsi_id = one.partner_id.purchase_gongsi_id


    def cron_update_gongsi_id(self):
        print('=cron_update_rate==')

        for one in self:
            print('===', one)
            one.gongsi_id = one.company_id.gongsi_id
            one.purchase_gongsi_id = one.company_id.gongsi_id


    # def update_hexiaotype_doing_type(self):
    #     for one in self:
    #         print('---',one)
    #         hexiao_type = False
    #         today = datetime.now()
    #         requested_date = one.requested_date
    #         # 未发货，开始发货，待核销，已核销
    #         doing_type = 'undelivered'
    #         if one.delivery_status == False:
    #             doing_type = 'undelivered'
    #         if one.delivery_status == 'undelivered' or one.delivery_status == 'partially_delivered':
    #             if requested_date and requested_date > (today - relativedelta(days=185)).strftime('%Y-%m-%d 00:00:00'):
    #                 doing_type = 'start_delivery'
    #             else:
    #                 if one.state != 'verification':
    #                     doing_type = 'wait_hexiao'
    #                     hexiao_type = 'abnormal'
    #                 else:
    #                     doing_type = 'has_hexiao'
    #                     hexiao_type = False
    #         if one.delivery_status == 'received':
    #             if one.balance == 0 and one.purchase_balance_sum == 0 :
    #                 if one.state != 'verification':
    #                     hexiao_type = 'write_off'
    #                     doing_type = 'wait_hexiao'
    #                 if one.state == 'verification':
    #                     doing_type = 'has_hexiao'
    #                     hexiao_type = False
    #             else:
    #                 hexiao_type = 'abnormal'
    #                 doing_type = 'wait_hexiao'
    #
    #         one.doing_type = doing_type
    #         one.hexiao_type = hexiao_type

    # def update_hexiaotype_doing_type(self):
    #     for one in self:
    #         print('---', one)
    #         hexiao_type = False
    #         state = one.state
    #         today = datetime.now()
    #         requested_date = one.requested_date
    #         # 未发货，开始发货，待核销，已核销
    #         if (one.delivery_status == 'undelivered' or one.delivery_status == 'partially_delivered') and requested_date and requested_date < (today - relativedelta(days=185)).strftime('%Y-%m-%d 00:00:00') and one.state != 'verification':
    #             state='verifying'
    #             hexiao_type = 'abnormal'
    #         if one.delivery_status == 'received' and one.state != 'verification':
    #             if one.balance == 0 and one.purchase_balance_sum3 == 0:
    #                 hexiao_type = 'write_off'
    #                 state = 'verifying'
    #             else:
    #                 hexiao_type = 'abnormal'
    #                 state = 'verifying'
    #         one.hexiao_type = hexiao_type
    #         one.state = state

    def update_hexiaotype_doing_type(self):
        for one in self:
            print('---', one)
            hexiao_type = False
            state = one.state
            today = datetime.now()
            requested_date = one.requested_date
            # 未发货，开始发货，待核销，已核销
            if one.state in ('sale','verifying'):
                if (one.no_sent_amount_new != 0 or one.purchase_no_deliver_amount_new != 0 ) and requested_date and requested_date < (today - relativedelta(days=185)).strftime('%Y-%m-%d 00:00:00'):
                    state='verifying'
                    hexiao_type = 'abnormal'
                if one.no_sent_amount_new == 0 and one.purchase_no_deliver_amount_new == 0:
                    if one.balance == 0 and one.purchase_balance_sum3 == 0:
                        hexiao_type = 'write_off'
                        state = 'verifying'
                    else:
                        hexiao_type = 'abnormal'
                        state = 'verifying'
            one.hexiao_type = hexiao_type
            one.state = state


    def action_verification(self):
        user = self.env.user
        if not user.has_group('sale.hegui_all') or not user.has_group('sales_team.group_manager'):
            raise Warning('非合规人员不允许核销！')
        if self.state != 'verifying':
            raise Warning('非待核销合同无法核销！')
        if self.hexiao_type == 'abnormal' and self.hexiao_comment == False:
            raise Warning('异常核销，请填写备注！')
        if self.purchase_delivery_status == False:
            raise Warning('采购合同还有未完成收货的，请核查！')
        self.state = 'verification'
        self.x_wkf_state = '199'
        self.hx_date = fields.date.today()
        self.no_sent_amount_new = 0
        self.purchase_balance_sum3 = 0
        self.purchase_no_deliver_amount_new = 0
        self.balance_new = 0

    def action_verification1(self):
        user = self.env.user

        self.state = 'verification'
        self.x_wkf_state = '199'
        self.hx_date = fields.date.today()
        self.no_sent_amount_new = 0


    def update_purchase_delivery(self):
        for one in self:
            if one.po_ids and all([x.delivery_status == 'received' for x in one.po_ids]):
                purchase_delivery_status = True
            else:
                purchase_delivery_status = False
            one.purchase_delivery_status = purchase_delivery_status


    def update_purchase_datas(self):
        for one in self:
             one.compute_purchase_balance3()
             one.compute_purchase_amount_total_new()
             one.compute_purchase_no_deliver_amount_new()

    #akiny
    def action_submit(self):
        war = ''
        if self.contract_code and self.partner_id and self.customer_pi and self.contract_date and self.current_date_rate > 0 and \
                self.requested_date and self.payment_term_id and self.order_line and self.contract_type and self.gongsi_id and\
                self.purchase_gongsi_id:
            self.state = 'submit'
        else:
            if not self.contract_code:
                war += '合同号不为空\n'
            if not self.partner_id:
                war += '客户不为空\n'
            if not self.customer_pi:
                war += '客户合同号不为空\n'
            if not self.contract_date:
                war += '客户确认日期不为空\n'
            if not self.payment_term_id:
                war += '付款条款不为空\n'
            if self.current_date_rate <= 0:
                war += '当日汇率不为0\n'
            if not self.order_line:
                war += '销售明细不为空\n'
            if not self.contract_type:
                war += '模式不为空\n'
            if not self.gongsi_id:
                war += '销售主体不为空\n'
            if not self.purchase_gongsi_id:
                war += '采购主体不为空\n'
            if war:
                raise Warning(war)