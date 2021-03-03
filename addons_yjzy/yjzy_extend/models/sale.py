# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from datetime import datetime
from odoo.exceptions import Warning
from .comm import BACK_TAX_RATIO
from dateutil.relativedelta import relativedelta

Stage_Status = [
    ('draft', '未开始'),
    ('confirmed', '就绪'),
    ('done', '完成'),
]
Stage_Status_Default = 'draft'

Sale_Selection = [('draft', '草稿'),
                  ('cancel', '取消'),
                  ('refused', u'拒绝'),
                  ('submit', u'待责任人审核'),
                  ('sales_approve', u'待业务合规审核'),
                  ('manager_approval', u'待总经理特批'),
                  ('approve', u'审批完成待出运'),
                  ('sale', '开始出运'),
                  ('abnormal', u'异常核销'),
                  ('verifying', u'正常核销'),
                  ('verification', u'核销完成'), ]


class SaleOrderStage(models.Model):
    _name = "sale.order.stage"
    _description = "Sale Order Stage"
    _order = 'sequence'

    name = fields.Char('Stage Name', translate=True, required=True)

    code = fields.Char('code')
    sequence = fields.Integer(help="Used to order the note stages", default=1)
    state = fields.Selection(Sale_Selection, 'State', default=Stage_Status_Default)  # track_visibility='onchange',
    fold = fields.Boolean('Folded by Default')
    # _sql_constraints = [
    #     ('name_code', 'unique(code)', u"编码不能重复"),
    # ]
    user_ids = fields.Many2many('res.users', 'ref_so_users', 'fid', 'tid', 'Users')  # 可以进行判断也可以结合自定义视图模块使用
    group_ids = fields.Many2many('res.groups', 'ref_so_group', 'gid', 'bid', 'Groups')


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
    # 13已添加，规则改变 所有的汇率都计算后填入 current_date_rate,之后全部用这个字段计算转汇
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

    # 13已添加
    def default_commission_ratio(self):
        return float(self.env['ir.config_parameter'].sudo().get_param('addons_yjzy.sale_commission', '0.015'))

    # 等待添加，这里的自动计算，有时候没有完成，需要再仔细观察一下
    @api.depends('aml_ids', 'state', 'yjzy_payment_ids', 'yjzy_payment_ids.amount', 'aml_ids.amount_currency',
                 'aml_ids.credit', 'aml_ids.debit', )
    def compute_balance_new(self):
        for one in self:
            if one.state != 'verification':
                sml_lines = one.aml_ids.filtered(lambda x: x.account_id.code == '2203')
                if one.yjzy_payment_ids and one.yjzy_payment_ids[0].currency_id.name == 'CNY':
                    balance = sum([x.credit - x.debit for x in sml_lines])
                    real_advance = sum([x.credit for x in sml_lines])
                else:
                    balance = sum([-1 * x.amount_currency for x in sml_lines])
                    # real_advance = 0
                    # for x in sml_lines:
                    # if x.amount_currency < 0:
                    #     print('amount_currency_akiny',x.amount_currency)
                    #     real_advance += x.amount_currency
                    real_advance = sum(
                        [-1 * x.amount_currency for x in sml_lines.filtered(lambda i: i.amount_currency < 0)])
                one.balance_new = balance
                one.real_advance = real_advance

    def compute_balance(self):
        for one in self:
            sml_lines = one.aml_ids.filtered(lambda x: x.account_id.code == '2203')
            if one.yjzy_payment_ids and one.yjzy_payment_ids[0].currency_id.name == 'CNY':
                balance = sum([x.credit - x.debit for x in sml_lines])
            else:
                balance = sum([-1 * x.amount_currency for x in sml_lines])
            one.balance = balance

    # 13已添加
    # @api.depends('po_ids')
    def compute_purchase_balance(self):
        for one in self:
            purchase_balance_sum = sum(one.po_ids.mapped('balance'))
            one.purchase_balance_sum = purchase_balance_sum

    @api.one
    @api.depends('po_ids_new.balance_new', 'po_ids_new')
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
    @api.depends('po_ids_new.amount_total', 'po_ids_new')
    def compute_purchase_amount_total_new(self):
        for one in self:
            if one.state != 'verification':
                print('total', one)
                purchase_amount_total = sum(one.po_ids_new.mapped('amount_total'))
                one.purchase_amount_total_new = purchase_amount_total

    # 13ok
    @api.depends('order_line.qty_delivered')
    def compute_no_sent_amount(self):
        for one in self:
            if one.state != 'verification':
                one.no_sent_amount_new = sum(
                    [x.price_unit * (x.product_uom_qty - x.qty_delivered) for x in one.order_line])

    # 13ok
    @api.one
    @api.depends('po_ids_new.no_deliver_amount_new', 'po_ids_new')
    def compute_purchase_no_deliver_amount_new(self):
        for one in self:
            if one.state != 'verification':
                print('total', one)
                one.purchase_no_deliver_amount_new = sum(one.po_ids_new.mapped('no_deliver_amount_new'))

    # @api.depends('po_ids.balance')
    def compute_po_residual(self):
        for one in self:
            one.advance_po_residual = sum([x.balance for x in one.po_ids])

    # ---------

    def compute_info(self):
        aml_obj = self.env['account.move.line']
        for one in self:
            one.tb_ids = one.order_line.mapped('tbl_ids').mapped('bill_id')
            one.tb_count = len(one.tb_ids)
            one.no_sent_amount = sum(
                [x.price_unit * (x.product_uom_qty - x.qty_delivered) for x in one.order_line])  # 13ok

            # 统计预收余额
            if one.payment_term_id:
                one.pre_advance = one.payment_term_id.get_advance(one.amount_total)
                print('====', one, one.pre_advance)

            ##金额统计
            lines = one.order_line
            if not lines: continue
            purchase_cost = one.company_currency_id.compute(sum([x.purchase_cost for x in lines]),
                                                            one.third_currency_id)
            fandian_amoun = one.company_currency_id.compute(sum([x.fandian_amoun for x in lines]),
                                                            one.third_currency_id)
            stock_cost = one.company_currency_id.compute(sum([x.stock_cost for x in lines]), one.third_currency_id)
            # 剩余出运数
            rest_tb_qty_total = sum(lines.mapped('rest_tb_qty'))
            # 样金计算
            gold_sample_state = 'none'
            line_count = len(one.order_line)
            line_count_gold = len(one.order_line.filtered(lambda x: x.is_gold_sample))

            if line_count_gold > 0:
                if line_count_gold == line_count:
                    gold_sample_state = 'all'
                else:
                    gold_sample_state = 'part'
            ps_state = 'none'
            line_count_ps = len(one.order_line.filtered(lambda x: x.is_ps))

            if line_count_ps > 0:
                if line_count_ps == line_count:
                    ps_state = 'all'
                else:
                    ps_state = 'part'

            if one.cip_type != 'normal':
                back_tax_amount = 0
            else:
                back_tax_amount = one.company_currency_id.compute(sum(x.back_tax_amount for x in lines),
                                                                  one.third_currency_id)

            amount_total2 = one._get_sale_amount()
            #  amount_total3 = one._get_amount_total3()
            commission_amount = one.commission_ratio * amount_total2

            #  commission_amount2 = one.commission_ratio * amount_total3

            other_cost = one._get_other_cost()

            vat_diff_amount = 0
            if one.include_tax and one.company_currency_id.name == 'CNY':
                vat_diff_amount = (one.amount_total2 - one.purchase_cost - one.stock_cost) / 1.13 * 0.13

            expense_cost_total = other_cost + commission_amount + vat_diff_amount

            profit_amount = (
                                        amount_total2 - purchase_cost - stock_cost - fandian_amoun - vat_diff_amount - other_cost - commission_amount + back_tax_amount) / 5
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

            one.rest_tb_qty_total = rest_tb_qty_total
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

            # one.fee_rmb_ratio = one.amount_total and one.company_currency_id.compute(one.fee_rmb_all + fandian_amoun + vat_diff_amount, one.currency_id) / one.amount_total * 100
            # akiny 用新的汇率计算
            one.fee_rmb_ratio = one.amount_total2 and (
                    one.fee_rmb_all + fandian_amoun + vat_diff_amount) / one.amount_total2 * 100
            one.fee_outer_ratio = one.amount_total and one.other_currency_id.compute(one.fee_outer_all,
                                                                                     one.currency_id) / one.amount_total * 100

            one.fee_all_ratio = amount_total2 and expense_cost_total / one.amount_total2 * 100

            one.profit_ratio = amount_total2 and profit_amount / amount_total2 * 100

            one.gross_profit = gross_profit
            one.gorss_profit_ratio = amount_total2 and (gross_profit / amount_total2 * 100)
            one.gold_sample_state = gold_sample_state
            one.ps_state = ps_state
            one.purchase_no_deliver_amount = purchase_no_deliver_amount
            one.purchase_approve_date = purchase_approve_date
            one.second_cost = sum(one.order_line.mapped('second_price_total'))
            one.second_porfit = one.amount_total2 - one.second_cost
            one.second_tenyale_profit = one.company_currency_id.compute(one.second_cost,
                                                                        one.third_currency_id) - one.purchase_cost - one.stock_cost
            one.commission_ratio_percent = one.commission_ratio * 100
            one.expense_cost_total = expense_cost_total

    @api.depends('yjzy_payment_ids', 'yjzy_payment_ids.amount')
    def compute_advance_total(self):
        for one in self:
            yjzy_payment_ids = one.yjzy_payment_ids.filtered(lambda x: x.state in ['posted', 'reconciled'])
            advance_total = sum(x.amount for x in yjzy_payment_ids)
            dlrs = one.advance_reconcile_order_line_ids
            advance_reconcile_order_line_amount_char = ''
            advance_reconcile_order_line_date_char = ''
            advance_reconcile_order_line_invoice_char = ''
            for o in dlrs:
                if o.amount_advance_org != 0:
                    advance_reconcile_order_line_amount_char += '%s\n' % (o.amount_advance_org)
                    advance_reconcile_order_line_date_char += '%s\n' % (o.order_id.date)
                    advance_reconcile_order_line_invoice_char += '%s\n' % (o.invoice_id)
            one.advance_reconcile_order_line_amount_char = advance_reconcile_order_line_amount_char
            one.advance_reconcile_order_line_date_char = advance_reconcile_order_line_date_char
            one.advance_total = advance_total

        # 814

    def _compute_po_include_tax(self):
        for one in self:
            po_include_tax = 'none'
            line_count = one.po_count
            line_count_include_tax = len(one.po_ids.filtered(lambda x: x.include_tax))
            if line_count_include_tax > 0:
                if line_count_include_tax == line_count:
                    po_include_tax = 'all'
                else:
                    po_include_tax = 'part'
            one.po_include_tax = po_include_tax

    def _comput_tb_line_count(self):
        for one in self:
            one.tb_line_count = len(one.tb_line_ids)

    @api.depends('partner_id')
    def compute_jituan(self):
        for one in self:
            jituan = one.partner_id.jituan_id
            one.jituan_id = jituan

    @api.model
    def _default_sale_order_stage(self):
        stage = self.env['sale.order.stage']
        return stage.search([], limit=1)

    @api.depends('hxd_ids', 'hxd_ids.amount_total_org_new')
    def compute_amount_org_hxd(self):
        for one in self:
            one.amount_org_hxd = sum(x.amount_total_org_new for x in one.hxd_ids)

    @api.depends('purchase_amount_total_new', 'amount_total')
    def compute_sale_purchase_percent(self):
        for one in self:
            sale_purchase_percent = one.purchase_amount_total_new / one.amount_total
            one.sale_purchase_percent = sale_purchase_percent

    stage_id = fields.Many2one(
        'sale.order.stage',
        default=_default_sale_order_stage, copy=False)

    state_1 = fields.Selection(Sale_Selection, u'审批流程', default='draft', index=True, related='stage_id.state',
                               track_visibility='onchange')  # 费用审批流程

    hxd_ids = fields.One2many('account.reconcile.order.line', 'so_id', '所有已经批准的核销单',
                              domain=[('order_id.state_1', 'in', ['done', 'post'])])
    amount_org_hxd = fields.Float('核销单的付款金额总和', compute=compute_amount_org_hxd, store=True)
    # 货币设置
    # 1013
    jituan_id = fields.Many2one('ji.tuan', '集团', compute=compute_jituan, store=True)
    # 825
    tb_line_ids = fields.One2many('transport.bill.line', 'so_id', u'出运明细')
    tb_line_count = fields.Integer('发运单计数', compute=_comput_tb_line_count)
    # 824
    po_include_tax = fields.Selection([('all', '全部含税'), ('part', '部分含税'), ('none', '不含税')], u'采购含税情况',
                                      compute=_compute_po_include_tax)  # 824
    # akiny715
    digits = fields.Selection([('2', '2'), ('3', '3'), ('4', '4')], '打印小数位数')
    advance_reconcile_order_line_ids = fields.One2many('account.reconcile.order.line', 'so_id', string='预收认领明细',
                                                       domain=[('order_id.state', '=', 'done'),
                                                               ('amount_total_org', '!=', 0)])
    advance_reconcile_order_line_amount_char = fields.Text(compute=compute_advance_total, string=u'预收认领明细金额')
    advance_reconcile_order_line_date_char = fields.Text(compute=compute_advance_total, string=u'预收认领日期')
    advance_reconcile_order_line_invoice_char = fields.Text(compute=compute_advance_total, string=u'预收认领对应账单')
    advance_total = fields.Monetary(u'预收总金额', compute=compute_advance_total, store=True)
    # 按照预收款为对象统计：因为没有做关联，所以通过销售合同进行

    company_currency_id = fields.Many2one('res.currency', u'公司货币',
                                          default=lambda self: self.env.user.company_id.currency_id.id)

    other_currency_id = fields.Many2one('res.currency', u'其他国外费用货币', default=lambda self: self.env.ref('base.USD').id)

    # 不需要
    third_currency_id = fields.Many2one('res.currency', u'统计货币',
                                        default=lambda self: self.env.user.company_id.currency_id.id)
    sale_currency_id = fields.Many2one('res.currency', related='currency_id', string=u'交易货币', store=True)
    product_manager_id = fields.Many2one('res.users', u'产品经理')
    incoterm_code = fields.Char(u'贸易术语', related='incoterm.code', readonly=True)
    cost_id = fields.Many2one('sale.cost', u'成本单', copy=False)

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
    # 。。。。。

    # 13已经添加
    contract_code = fields.Char(u'合同编码')
    contract_date = fields.Date(u'签订日期')
    link_man_id = fields.Many2one('res.partner', u'联系人')
    sale_assistant_id = fields.Many2one('res.users', u'业务助理')
    partner_payment_term_id = fields.Many2one('account.payment.term', u'客户付款条款',
                                              related='partner_id.property_payment_term_id')
    contract_type = fields.Selection([('a', '模式1'), ('b', '模式2'), ('c', '模式3')], '合同类型', default='c')
    gongsi_id = fields.Many2one('gongsi', '内部公司')
    purchase_gongsi_id = fields.Many2one('gongsi', '内部采购公司')
    cip_type = fields.Selection([('normal', u'正常报关'), ('buy', u'买单报关'), ('none', '不报关')], string=u'报关',
                                default='normal')
    current_date_rate = fields.Float('当日汇率', group_operator=False)  # akiny参考group不汇总计算
    include_tax = fields.Boolean(u'含税')
    stock_cost = fields.Monetary(u'库存成本', currency_field='third_currency_id', compute=compute_info)
    commission_amount = fields.Monetary(u'经营计提金额', currency_field='third_currency_id', compute=compute_info)
    commission_ratio = fields.Float(u'经营计提比', digits=(2, 4), default=lambda self: self.default_commission_ratio())
    commission_ratio_percent = fields.Float(u'经营计提比%', compute=compute_info)
    approve_date = fields.Date('审批完成日期')
    approve_uid = fields.Many2one('res.users', u'完成审批人')
    gold_sample_state = fields.Selection([('all', '全部有'), ('part', '部分有'), ('none', '无金样')], '样金管理',
                                         compute=compute_info)
    ps_state = fields.Selection([('all', '全部有'), ('part', '部分有'), ('none', '无PS')], 'PS管理',
                                compute=compute_info)
    customer_pi = fields.Char(u'客户订单号')
    fee_inner = fields.Monetary(u'国内运杂费', currency_field='company_currency_id')
    fee_rmb1 = fields.Monetary(u'人民币费用1', currency_field='company_currency_id')
    fee_rmb2 = fields.Monetary(u'人民币费用2', currency_field='company_currency_id')
    fee_outer = fields.Monetary(u'国外运保费', currency_field='other_currency_id')
    outer_currency_id = fields.Many2one('res.currency', u'国外运保费货币', )
    fee_export_insurance = fields.Monetary(u'出口保险费', currency_field='other_currency_id')
    export_insurance_currency_id = fields.Many2one('res.currency', u'出口保险费货币')
    fee_other = fields.Monetary(u'其他外币费用', currency_field='other_currency_id')
    # 通过onchange的方式，保证13 的目前客户的使用体验不变
    fee_rmb2_note = fields.Text(u'人名币备注2')
    fee_rmb1_note = fields.Text(u'人名币备注1')
    fee_other_note = fields.Text(u'外币备注1')
    tb_ids = fields.Many2many('transport.bill', 'ref_tb_so', 'tb_id', 'so_id', string=u'出运单', compute=compute_info)
    tb_count = fields.Integer('发运单计数', compute=compute_info)
    is_different_payment_term = fields.Boolean('付款条款是否不同')
    is_editable = fields.Boolean(u'可编辑')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('check', u'检查'),
        ('submit', u'待责任人审核'),
        ('sales_approve', u'待业务合规审核'),
        ('manager_approval', u'待总经理特批'),
        ('approve', u'审批完成待出运'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
        ('refuse', u'拒绝'),
        ('abnormal', u'异常'),
        ('verifying', u'待核销'),
        ('verification', u'核销完成'),
    ], string='Status', readonly=True, copy=False, index=True, track_visibility='onchange', default='draft')
    no_sent_amount = fields.Monetary(u'未发货的金额', compute=compute_info)
    no_sent_amount_new = fields.Monetary(u'未发货的金额', compute=compute_no_sent_amount, store=True)

    purchase_no_deliver_amount = fields.Float('未发货的采购金额', compute=compute_info)
    purchase_no_deliver_amount_new = fields.Float('未发货的采购金额', compute='compute_purchase_no_deliver_amount_new',
                                                  store=True)
    po_ids_new = fields.One2many('purchase.order', 'source_so_id', '采购合同新')
    purchase_delivery_status = fields.Boolean('采购发货完成', compute='update_purchase_delivery')
    from_wharf_id = fields.Many2one('stock.wharf', u'目的港POD')
    to_wharf_id = fields.Many2one('stock.wharf', u'目的港POL')
    mark_text = fields.Text(u'唛头')

    submit_date = fields.Date('提交审批时间', copy=False)  # 13取消
    submit_uid = fields.Many2one('res.users', u'提交审批', copy=False)  # 13取消
    sales_confirm_date = fields.Date('责任人审批时间', copy=False)  # 13取消
    sales_confirm_uid = fields.Many2one('res.users', u'责任人审批', copy=False)  # 13取消
    hegui_date = fields.Date('合规审批日期', copy=False)  # 13换字段名
    hegui_uid = fields.Many2one('res.users', u'合规审批', copy=False)  # 13换字段名
    hx_date = fields.Date('核销时间', copy=False)
    purchase_approve_date = fields.Datetime('采购审批时间', compute=compute_info)
    rest_tb_qty_total = fields.Float(u'出运总数', compute=compute_info)
    # ---------

    # transport_bill_id = fields.Many2one('transport.bill', u'出运单', copy=False)
    is_cip = fields.Boolean(u'报关', default=True)

    # 其他费用  fee_inner,fee_rmb1,fee_rmb2,fee_outer,fee_export_insurance,fee_other

    fee_rmb_all = fields.Monetary(u'人民币费用合计', currency_field='company_currency_id', compute=compute_info)
    fee_rmb_ratio = fields.Float(u'人名币费用占销售额比', digits=(2, 2), compute=compute_info)  # akiny 4改成了2
    fee_outer_all = fields.Monetary(u'外币费用合计', currency_field='other_currency_id', compute=compute_info)
    fee_outer_ratio = fields.Float(u'外币费用占销售额比', digits=(2, 2), compute=compute_info)  # akiny 4改成了2
    fee_all_ratio = fields.Float(u'总费用占比', digits=(2, 2), compute=compute_info)  # akiny 4改成了2

    pre_advance = fields.Monetary(u'预收金额', currency_field='currency_id', compute=compute_info, store=False)
    advance_po_residual = fields.Float(u'预付余额', compute=compute_po_residual, store=True)
    yjzy_payment_ids = fields.One2many('account.payment', 'so_id', u'预收认领单')
    yjzy_currency_id = fields.Many2one('res.currency', u'预收币种', related='yjzy_payment_ids.currency_id')

    balance = fields.Monetary(u'预收余额', compute=compute_balance, currency_field='yjzy_currency_id')
    balance_new = fields.Monetary(u'预收余额', compute=compute_balance_new, currency_field='yjzy_currency_id', store=True)
    real_advance = fields.Monetary(u'预收金额', compute=compute_balance_new, currency_field='yjzy_currency_id', store=True)
    exchange_rate = fields.Float(u'目前汇率', compute=compute_exchange_rate, digits=(2, 2))  # akiny 4改成了2
    appoint_rate = fields.Float(u'使用汇率', digits=(2, 6))
    # currency_tate = fields.Many2one('res.currency.rate',u'系统汇率')
    # country_id = fields.Many2one('res.country', related='partner_id.country_id', string=u'国别', readonly=True)
    term_description = fields.Html(u'销售条款')
    state2 = fields.Selection(
        [('draft', u'草稿'), ('to_approve', u'待批准'), ('edit', u'可修改'), ('confirmed', u'待审批'), ('done', u'审批完成')], u'状态',
        default='draft')
    amount_total2 = fields.Monetary(u'销售金额', currency_field='third_currency_id', compute=compute_info)
    # akiny 手动汇率
    # amount_total3 = fields.Monetary(u'销售金额', currency_field='third_currency_id', compute=compute_info)

    purchase_cost = fields.Monetary(u'采购成本', currency_field='third_currency_id', compute=compute_info)
    purchase_stock_cost = fields.Monetary(u'采购库存成本合计', currency_field='third_currency_id', compute=compute_info)
    fandian_amoun = fields.Monetary(u'返点金额', currency_field='third_currency_id', compute=compute_info)

    lines_profit_amount = fields.Monetary(u'明细利润计总', currency_field='third_currency_id')
    other_cost = fields.Monetary(u'其他费用总计', currency_field='third_currency_id', compute=compute_info)

    expense_cost_total = fields.Monetary(u'所有费用总和', currency_field='third_currency_id', compute=compute_info)

    back_tax_amount = fields.Monetary(u'退税金额', currency_field='third_currency_id', compute=compute_info)
    profit_amount = fields.Monetary(u'净利润', currency_field='third_currency_id', compute=compute_info)
    profit_ratio = fields.Float(u'净利润率%', compute=compute_info)

    gross_profit = fields.Monetary(u'毛利', currency_field='third_currency_id', compute=compute_info)
    gorss_profit_ratio = fields.Float(u'毛利率%', compute=compute_info)
    pdt_value_id = fields.Many2one('product.attribute.value', string=u'产品属性', readonly=True,
                                   help=u'只是为在SO上搜索属性,不直接记录数据')
    # is_tb_process = fields.Boolean(u'出运单运行中', help='是否有关联的出运单还未结案?')

    vat_diff_amount = fields.Monetary(u'增值税差额', currency_field='third_currency_id', compute=compute_info)
    mark_comb_id = fields.Many2one('mark.comb', u'唛头组')

    display_detail = fields.Boolean(u'显示详情')
    aml_ids = fields.One2many('account.move.line', 'so_id', u'分录明细', readonly=True)
    approvaled_date = fields.Datetime('审批完成时间')

    # akiny 增加state
    # state = fields.Selection(selection_add=[('refuse', u'拒绝'), ('submit', u'已提交'),('sales_approve', u'责任人已审批'),
    #     ('approve', u'审批完成'), ('manager_approval', u'待总经理审批'),
    #     ('verifying', u'核销中'), ('verification', u'核销完成')],readonly=False)

    purchase_balance_sum = fields.Float('采购预付余额', compute='compute_purchase_balance')
    purchase_balance_sum3 = fields.Float('采购预付余额', compute='compute_purchase_balance3', store=True)
    # purchase_balance_sum2 = fields.Float('采购预付余额',compute='compute_purchase_balance2',store=True)
    purchase_amount_total_new = fields.Float('采购金额', compute='compute_purchase_amount_total_new', store=True)
    purchase_amount_total = fields.Float('采购金额', compute='compute_purchase_amount_total')

    second_cost = fields.Float('销售主体成本', compute=compute_info)  # second_amoun
    second_porfit = fields.Float('销售主体利润', compute=compute_info)  # amount_total2-刚刚计算出来的 second_const
    second_tenyale_profit = fields.Float('采购主体利润', compute=compute_info)  # (采购主体利润)：

    hexiao_type = fields.Selection([('abnormal', u'异常核销'), ('write_off', u'正常核销')], string='核销类型')

    hexiao_comment = fields.Text(u'异常核销备注')
    doing_type = fields.Selection([('undelivered', u'未发货'), ('start_delivery', u'开始发货'),
                                   ('wait_hexiao', u'待核销'), ('has_hexiao', u'已核销')],
                                  u'出运与核销状态')

    sale_purchase_percent = fields.Float('采购销售比',digits=(2,2),compute=compute_sale_purchase_percent,store=True)


    # purchase_update_date = fields.Datetime(u'采购更新的时间')

    # 更新
    def open_wizard_multi_sale_line(self):
        # war = ''
        # if not self.date:
        #     war += '请填写出运日期\n'
        # if self.current_date_rate ==0:
        #     war += '单日汇率不为零\n'
        # if war:
        #     raise Warning(war)
        # else:
        self.ensure_one()
        ctx = self.env.context.copy()
        product_ids = self.order_line.mapped('product_id')
        ctx.update({'default_so_id': self.id,
                    'default_so_product_ids': product_ids.ids
                    })
        return {
            'name': '添加销售明细',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.multi.sale.line',
            # 'res_id': bill.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': ctx,
        }

    def _stage_find(self, domain=None, order='sequence'):
        search_domain = list(domain)
        return self.env['sale.order.stage'].search(search_domain, order=order, limit=1)

    # 新的审批流程
    def action_submit_stage(self):
        for line in self.order_line:
            if line.product_uom_qty != line.dlr_qty:
                raise Warning('采购和销售的数量不匹配，请检查！')
        self.action_submit()
        stage_id = self._stage_find(domain=[('code', '=', '020')])
        return self.write({'stage_id': stage_id.id,
                           # 'state': 'submit',
                           'submit_uid': self.env.user.id,
                           'submit_date': fields.datetime.now()})

    def action_sales_approve_stage(self):
        stage_id = self._stage_find(domain=[('code', '=', '030')])
        return self.write({'stage_id': stage_id.id,
                           'state': 'sales_approve',
                           'sales_confirm_uid': self.env.user.id,
                           'sales_confirm_date': fields.datetime.now()})

    def action_approve_stage(self):
        self.check_po_allow()
        self.action_Warning()
        stage_id = self._stage_find(domain=[('code', '=', '050')])
        return self.write({'stage_id': stage_id.id,
                           'state': 'approve',
                           'approve_uid': self.env.user.id,
                           'approve_date': fields.datetime.now()})

    def action_to_manager_stage(self):
        stage_id = self._stage_find(domain=[('code', '=', '040')])
        return self.write({'stage_id': stage_id.id,
                           'state': 'manager_approval',
                           'hegui_uid': self.env.user.id,
                           'hegui_date': fields.datetime.now()})

    def action_confirm_stage(self):
        self.action_confirm_new()
        stage_id = self._stage_find(domain=[('code', '=', '060')])
        return self.write({'stage_id': stage_id.id,
                           })

    def action_refuse_stage(self, reason):
        stage_id = self._stage_find(domain=[('code', '=', '100')])
        stage_preview = self.stage_id
        user = self.env.user
        group = self.env.user.groups_id
        if user not in stage_preview.user_ids:
            raise Warning('您没有权限拒绝')
        else:
            self.write({'state': 'refuse',
                        'submit_date': False,
                        'submit_uid': False,
                        'sales_confirm_date': False,
                        'sales_confirm_uid': False,
                        'approve_date': False,
                        'approve_uid': False,
                        'stage_id': stage_id.id})
        for so in self:
            so.message_post_with_view('yjzy_extend.so_template_refuse_reason',
                                      values={'reason': reason, 'name': self.contract_code},
                                      subtype_id=self.env.ref(
                                          'mail.mt_note').id)  # 定义了留言消息的模板，其他都可以参考，还可以继续参考费用发送计划以及邮件方式

    # 核销的动作还要再考虑：核销完成后，又要退回了， 所以我们那个新的核销后 清零的数量的字段有么有用
    def action_to_draft_stage(self):
        stage_id = self._stage_find(domain=[('code', '=', '010')])
        self.write({'state': 'draft',
                    'stage_id': stage_id.id})

    def action_to_cancel_stage(self):
        if self.create_uid.id != self.env.user.id:
            raise Warning('只有创建者才允许取消！')
        if self.state not in ['draft', 'refuse']:
            raise Warning('只有草稿或者拒绝状态的才能取消')
        self.action_cancel()
        stage_id = self._stage_find(domain=[('code', '=', '110')])
        self.write({
            'submit_date': False,
            'submit_uid': False,
            'sales_confirm_date': False,
            'sales_confirm_uid': False,
            'approve_date': False,
            'approve_uid': False,
            'stage_id': stage_id.id})

    # 0917手动进入待核销
    def action_manual_ubnormal_hexiao(self):
        self.hexiao_type = 'abnormal'
        self.state = 'done'

    # 13已经添加
    @api.constrains('current_date_rate', 'fee_inner')
    def check_fields(self):
        if self.current_date_rate <= 0:
            raise Warning(u'汇率必须大于0')

    @api.constrains('contract_code')
    def check_contract_code(self):
        for one in self:
            if self.search_count([('contract_code', '=', one.contract_code)]) > 1:
                raise Warning('合同编码重复')

    # akiny 加入对是否使用今日手填汇率的判断
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
            other_cost = (
                                 self.fee_outer + self.fee_export_insurance + self.fee_other) * self.current_date_rate + self.fee_inner + self.fee_rmb1 + self.fee_rmb2
            return other_cost

        else:
            return sum([self.company_currency_id.compute(self.fee_inner, self.third_currency_id),
                        self.company_currency_id.compute(self.fee_rmb1, self.third_currency_id),
                        self.company_currency_id.compute(self.fee_rmb2, self.third_currency_id),
                        self.outer_currency_id.compute(self.fee_outer, self.third_currency_id),
                        self.export_insurance_currency_id.compute(self.fee_export_insurance,
                                                                  self.third_currency_id),
                        self.other_currency_id.compute(self.fee_other, self.third_currency_id),
                        ])

    # akiny 加入对是否使用今日手填汇率的判断
    def _get_other_cost_no_rmb(self):
        if self.company_id.is_current_date_rate:
            other_cost_no_rmb = (
                                        self.fee_outer + self.fee_export_insurance + self.fee_other) * self.current_date_rate
            return other_cost_no_rmb
        else:
            return sum([self.outer_currency_id.compute(self.fee_outer, self.third_currency_id),
                        self.export_insurance_currency_id.compute(self.fee_export_insurance,
                                                                  self.third_currency_id),
                        self.other_currency_id.compute(self.fee_other, self.third_currency_id),
                        ])

    def _get_sale_commission(self, sale_amount):
        sale_commission_ratio = float(
            self.env['ir.config_parameter'].sudo().get_param('addons_yjzy.sale_commission', '0.015'))
        return sale_commission_ratio, sale_amount * sale_commission_ratio

    def get_appoint_rate(self):
        self.ensure_one()
        self.appoint_rate = self.exchange_rate

    # --------
    # : 公式的cost改成second_cost
    # second_tenyale_profit：原公式的销售额改成second_cost
    # second_unit_price: = 订单
    # 手动计算采购单balance
    def compute_purchase_balance4(self):
        print('---', self)
        purchase_balance_sum = sum(self.po_ids.mapped('balance_new'))
        self.purchase_balance_sum4 = purchase_balance_sum

    # 13ok
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
            self.gongsi_id = gongsi_obj.search([('name', '=', 'BERTZ')], limit=1)
            self.purchase_gongsi_id = gongsi_obj.search([('name', '=', '天宇进出口')], limit=1)

        else:
            self.is_inner_trade = False

    @api.onchange('second_company_id')
    def onchange_second_company(self):
        self.second_partner_id = self.second_company_id.partner_id

    @api.multi
    def copy(self, default=None):
        default = dict(default or {})
        if 'contract_code' not in default:
            default['contract_code'] = "%s(copy)" % self.contract_code
        return super(sale_order, self).copy(default)

    # @api.multi
    # def write(self, vals):
    #     body = '%s' % vals
    #     self.message_post(body=body, subject='内容修改', message_type='notification')
    #     return super(sale_order, self).write(vals)

    def unlink(self):
        for one in self:
            if one.state != 'cancel':
                raise Warning(u'只有可删除状态订单允许删除')
        return super(sale_order, self).unlink()

    # 13ok
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

    # 13ok
    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.term_description = self.partner_id.term_description
        self.user_id = self.partner_id.user_id
        self.sale_assistant_id = self.partner_id.assistant_id
        self.product_manager_id = self.partner_id.product_manager_id
        self.contract_type = self.partner_id.contract_type
        self.gongsi_id = self.partner_id.gongsi_id
        self.purchase_gongsi_id = self.partner_id.purchase_gongsi_id
        self.link_man_id = self.partner_id.child_ids and self.partner_id.child_ids[0]
        self.mark_text = self.partner_shipping_id.mark_text
        self.from_wharf_id = self.partner_shipping_id.wharf_src_id
        self.to_wharf_id = self.partner_shipping_id.wharf_dest_id
        # self.jituan_id = self.partner_id.jituan_id
        return super(sale_order, self).onchange_partner_id()

    def open_advance_residual_lines(self):
        self.ensure_one()
        lines = self.env['account.move.line'].search([('so_id', '=', self.id)]).filtered(
            lambda x: x.account_id.code == '2203')
        return {
            'name': _(u'订单预收分录明细'),
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'account.move.line',
            'type': 'ir.actions.act_window',
            'domain': [('id', '=', [x.id for x in lines])],
            'target': 'new',
        }

    # 825
    def open_view_tb_line(self):
        self.ensure_one()
        tree_view = self.env.ref('yjzy_extend.view_transport_bill_line_tenyale_tree')
        return {
            'name': _(u'出运明细'),
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'transport.bill.line',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree')],
            'domain': [('id', 'in', [x.id for x in self.tb_line_ids])],
            # 'context':{'search_default_group_by_bill_id':1}
        }

    # 13ok
    def open_view_transport_bill(self):
        self.ensure_one()
        tree_view = self.env.ref('yjzy_extend.view_transport_bill_new_sales_tree')
        form_view = self.env.ref('yjzy_extend.view_transport_bill_new_sales_form')
        return {
            'name': _(u'出运合同'),
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'transport.bill',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('id', 'in', [x.id for x in self.tb_ids])]
        }

    # 13ok
    def action_confirm(self):
        '''so auto po confirm'''
        res = super(sale_order, self).action_confirm()
        # akiny to approve的时候触发button_approve
        todo_po = self.po_ids.filtered(
            lambda x: x.can_confirm_by_so and x.state not in ['purchase', 'done', 'cancel', 'edit'])
        todo_po1 = self.po_ids.filtered(lambda x: x.can_confirm_by_so and x.state in ['to approve'])

        #  if todo_po:
        #      todo_po.button_confirm()
        if todo_po1:
            todo_po1.button_approve()

        # for po in todo_po:
        #     if po.state == 'to approve':
        #         po.button_approve()
        #
        #     else:
        #         po.button_confirm()

        return res

    def action_confirm_new(self):
        '''so auto po confirm'''
        res = super(sale_order, self).action_confirm()
        # akiny to approve的时候触发button_approve
        todo_po = self.po_ids.filtered(
            lambda x: x.can_confirm_by_so and x.state not in ['purchase', 'done', 'cancel', 'edit'])
        todo_po1 = self.po_ids.filtered(lambda x: x.can_confirm_by_so and x.state in ['to approve'])

        #  if todo_po:
        #      todo_po.button_confirm()
        if todo_po1:
            # todo_po1.button_approve()
            for po in todo_po1:
                po.action_confirm_stage()
        # for po in todo_po:
        #     if po.state == 'to approve':
        #         po.button_approve()
        #
        #     else:
        #         po.button_confirm()
        return res

    def action_confirm2(self):
        self.ensure_one()
        self.state2 = 'confirmed'

    def action_done2(self):
        self.ensure_one()
        self.state2 = 'done'

    def _check_done(self):
        pass

    # 13ok
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
        # 保证bom完整

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
                raise Warning(u'PO-%s审批还未完成' % po.comtract_code)
        return True

    def update_back_tax(self):
        self.ensure_one()
        for line in self.order_line:
            line.back_tax = self.cip_type != 'none' and line.product_id.back_tax or 0

        self.compute_info()

    # 13取消
    @api.model
    def cron_update_rate(self):
        print('=cron_update_rate==')
        currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
        for one in self.search(['|', ('current_date_rate', '=', 0), ('current_date_rate', '=', False)]):
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

    # 1.发货完成的合同，且没有待认领预收付的，进正常待核销，发货完成当天进去;
    # 2.发货完成的合同，有预收付款的，认领完成后，进正常待核销，认领完成和发货完成，两者最后完成的日期当天进去
    # 3.发货完成的合同，有预收付款的，超出90天未认领完成的，进异常待核销，90天到期日当天进去;
    # 4.未发货完成的合同，离约定发货日期180天的，进异常待核销，180天到期当天进去
    # 1116 正式，加入stage
    def update_hexiaotype_doing_type(self):
        for one in self:
            print('---', one)
            hexiao_type = False
            state = one.state
            today = datetime.now()
            requested_date = one.requested_date
            stage_id = one.stage_id
            # 未发货，开始发货，待核销，已核销
            if one.state in ('sale', 'done', 'verifying'):
                if (
                        one.no_sent_amount_new != 0 or one.purchase_no_deliver_amount_new != 0) and requested_date and requested_date < (
                        today - relativedelta(days=180)).strftime('%Y-%m-%d 00:00:00'):
                    state = 'done'
                    hexiao_type = 'abnormal'
                    stage_id = self._stage_find(domain=[('code', '=', '080')])
                if one.no_sent_amount_new == 0 and one.purchase_no_deliver_amount_new == 0:
                    if one.balance == 0 and one.purchase_balance_sum3 == 0:
                        hexiao_type = 'write_off'
                        state = 'done'
                        stage_id = self._stage_find(domain=[('code', '=', '070')])
                    else:
                        if requested_date and requested_date < (today - relativedelta(days=90)).strftime(
                                '%Y-%m-%d 00:00:00'):
                            hexiao_type = 'abnormal'
                            state = 'done'
                            stage_id = self._stage_find(domain=[('code', '=', '080')])
            one.hexiao_type = hexiao_type
            one.state = state
            one.stage_id = stage_id

    # 增加state:异常合同，将待核销的二级分组的异常核销进入state的异常合同
    def update_hexiaotype_doing_type_new(self):
        for one in self:
            print('---', one)
            hexiao_type = False
            state = one.state
            today = datetime.now()
            requested_date = one.requested_date
            # 未发货，开始发货，待核销，已核销
            if one.state in ('sale', 'done', 'verifying'):
                if (
                        one.no_sent_amount_new != 0 or one.purchase_no_deliver_amount_new != 0) and requested_date and requested_date < (
                        today - relativedelta(days=180)).strftime('%Y-%m-%d 00:00:00'):
                    state = 'abnormal'
                    hexiao_type = 'abnormal'
                if one.no_sent_amount_new == 0 and one.purchase_no_deliver_amount_new == 0:
                    if one.balance == 0 and one.purchase_balance_sum3 == 0:
                        if hexiao_type == 'abnormal':
                            hexiao_type = 'abnormal'
                            state = 'done'
                        else:
                            hexiao_type = 'write_off'
                            state = 'done'
                    else:
                        if requested_date and requested_date < (today - relativedelta(days=90)).strftime(
                                '%Y-%m-%d 00:00:00'):
                            hexiao_type = 'abnormal'
                            state = 'abnormal'
            one.hexiao_type = hexiao_type
            one.state = state

    def action_verification(self):
        user = self.env.user
        if not user.has_group('sale.hegui_all') or not user.has_group('sales_team.group_manager'):
            raise Warning('非合规人员不允许核销！')
        if self.state != 'done':
            raise Warning('非待核销合同无法核销！')
        if self.hexiao_type == 'abnormal' and self.hexiao_comment == False:
            raise Warning('异常核销，请填写备注！')
        if self.purchase_delivery_status == False:
            raise Warning('采购合同还有未完成收货的，请核查！')
        stage_id = self._stage_find(domain=[('code', '=', '090')])
        self.stage_id = stage_id
        self.state = 'verification'
        self.x_wkf_state = '199'
        self.hx_date = fields.date.today()
        self.no_sent_amount_new = 0
        self.purchase_balance_sum3 = 0
        self.purchase_no_deliver_amount_new = 0
        self.balance_new = 0

    def action_verification_new(self):
        user = self.env.user
        if not user.has_group('sale.hegui_all') or not user.has_group('sales_team.group_manager'):
            raise Warning('非合规人员不允许核销！')
        if self.state != 'done':
            raise Warning('非待核销合同无法核销！')
        if self.hexiao_type == 'abnormal' and self.hexiao_comment == False:
            raise Warning('异常核销，请填写备注！')
        if self.purchase_delivery_status == False:
            raise Warning('采购合同还有未完成收货的，请核查！')
        self.state = 'verification'
        self.x_wkf_state = '199'
        self.hx_date = fields.date.today()

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

    # akiny
    def action_submit(self):
        self.action_Warning()
        war = ''
        if self.contract_code and self.partner_id and self.customer_pi and self.contract_date and self.current_date_rate > 0 and \
                self.requested_date and self.payment_term_id and self.order_line and self.contract_type and self.gongsi_id and \
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

    def action_Warning(self):
        war = ''
        if self.partner_id.state != 'done':
            war = '客户正在审批中，请先完成客户的审批'
        if len(self.order_line.filtered(lambda x: x.supplier_id.state != 'done')) > 0:
            war = '供应商正在审批中，请先完成供应商的审批'
        if war != '':
            raise Warning(war)
        else:
            return True
