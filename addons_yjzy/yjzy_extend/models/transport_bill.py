# -*- coding: utf-8 -*-
from num2words import num2words
from odoo.addons import decimal_precision as dp
from odoo import models, fields, api, _
from odoo.exceptions import Warning
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF

Stage_Status = [
    ('draft', '未开始'),
    ('confirmed', '就绪'),
    ('done', '完成'),
]
Stage_Status_Default = 'draft'

Transport_Selection = [('cancel', u'取消'),
                       ('refused', u'已拒绝'),
                       ('draft', u'草稿'),
                       ('submit', u'待责任人审批'), ('sales_approve', u'待合规审批'), ('manager_approve', u'总经理审批'),
                       ('approve', u'合规已审批'), ('delivered', u'发货完成'),
                       ('invoiced', u'账单已确认'), ('abnormal', u'异常待核销'),
                       # ('locked', u'锁定并等待增加采购完成'),('finish_add_purchase','完成增加采购'),
                       ('verifying', u'待核销'),
                       ('done', u'已核销'), ('paid', '已收款'), ('edit', u'可修改')]


class TransportStage(models.Model):
    _name = "transport.bill.stage"
    _description = "Transport Stage"
    _order = 'sequence'

    name = fields.Char('Stage Name', translate=True, required=True)
    code = fields.Char('code')
    sequence = fields.Integer(help="Used to order the note stages", default=1)
    state = fields.Selection(Transport_Selection, 'State',
                             default=Transport_Selection[0][0])  # track_visibility='onchange',
    fold = fields.Boolean('Folded by Default')
    # _sql_constraints = [
    #     ('name_code', 'unique(code)', u"编码不能重复"),
    # ]
    user_ids = fields.Many2many('res.users', 'ref_tb_users', 'fid', 'tid', 'Users')  # 可以进行判断也可以结合自定义视图模块使用
    group_ids = fields.Many2many('res.groups', 'ref_tb_group', 'gid', 'bid', 'Groups')


class transport_bill(models.Model):
    _name = 'transport.bill'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '发运单'
    _order = 'id desc'

    def compute_info(self):
        for one in self:
            if (not one.outer_currency_id) or (not one.sale_currency_id) or (not one.third_currency_id):
                # print(u'币种数据不全，不计算')
                continue
            # one.invoice_in_ids = one.sale_invoice_id + one.back_tax_invoice_id
            moves = one.line_ids.mapped('move_ids')
            one.move_ids = moves
            one.stage1move_ids = moves.filtered(lambda x: x.picking_code == 'incoming')
            one.stage2move_ids = moves.filtered(lambda x: x.picking_code == 'outgoing')
            pickings = one.move_ids.mapped('picking_id')
            one.picking_ids = pickings
            one.stage1picking_ids = pickings.filtered(lambda x: x.picking_type_code == 'incoming')
            one.stage2picking_ids = pickings.filtered(lambda x: x.picking_type_code == 'outgoing')
            # 计算统计金额
            lines = one.line_ids
            if not lines: continue
            org_sale_amount, sale_amount = one._get_sale_amount(lines)
            org_real_sale_amount = sum([x.amount for x in one.hsname_ids])

            current_date_rate = one.current_date_rate
            if one.company_id.is_current_date_rate:
                real_sale_amount = org_real_sale_amount * current_date_rate
                purchase_cost = sum(x.purchase_cost for x in lines)
                stock_cost = sum(x.stock_cost for x in lines)
                other_cost = one._get_other_cost()
                if one.cip_type != 'normal':
                    back_tax_amount = 0
                    back_tax_amount_org = 0
                else:
                    back_tax_amount = sum(x.back_tax_amount2 for x in one.btls_hs_ids)
                    back_tax_amount_org = sum(x.back_tax_amount for x in one.line_ids)
            else:
                real_sale_amount = one.third_currency_id and one.sale_currency_id.compute(org_real_sale_amount,
                                                                                          one.third_currency_id) or 0
                purchase_cost = one.company_currency_id.compute(sum(x.purchase_cost for x in lines),
                                                                one.third_currency_id)
                stock_cost = one.company_currency_id.compute(sum(x.stock_cost for x in lines), one.third_currency_id)
                other_cost = one.company_currency_id.compute(one._get_other_cost(), one.third_currency_id)
                if one.cip_type != 'normal':
                    back_tax_amount = 0
                    back_tax_amount_org = 0
                else:
                    back_tax_amount = one.company_currency_id.compute(sum(x.back_tax_amount2 for x in one.btls_hs_ids),
                                                                      one.third_currency_id)
                    back_tax_amount_org = one.company_currency_id.compute(sum(x.back_tax_amount for x in one.line_ids),
                                                                          one.third_currency_id)
            fandian_amount = sum([x.fandian_amount for x in one.fandian_ids])  ##### 不含税）采购金额*返点比例，（含税）采购金额*0.87*返点比例

            # back_tax_amount = one.company_currency_id.compute(sum(x.back_tax_amount for x in lines), one.third_currency_id)
            # 样金计算 akiny

            gold_sample_state = 'none'
            line_count = len(one.line_ids)
            line_count_gold = len(one.line_ids.filtered(lambda x: x.is_gold_sample))

            if line_count_gold > 0:
                if line_count_gold == line_count:
                    gold_sample_state = 'all'
                else:
                    gold_sample_state = 'part'

            ps_state = 'none'
            line_count_ps = len(one.line_ids.filtered(lambda x: x.is_ps))
            if line_count_ps > 0:
                if line_count_ps == line_count:
                    ps_state = 'all'
                else:
                    ps_state = 'part'

            # 计算账单是否确认
            invoice_state = 'draft'
            line_count = len(one.all_invoice_ids)
            line_count_open = len(one.all_invoice_ids.filtered(lambda x: x.state in ['open', 'paid']))
            if line_count_open > 0:
                if line_count_open == line_count:
                    invoice_state = 'open'
                else:
                    invoice_state = 'draft'
            one.invoice_state = invoice_state
            one.date_out_in_att_count = len(one.date_out_in_att)
            one.date_ship_att_count = len(one.date_ship_att)
            one.date_customer_finish_att_count = len(one.date_customer_finish_att)


            sale_commission_amount = real_sale_amount * one.sale_commission_ratio

            vat_diff_amount = 0
            if one.include_tax and one.company_currency_id.name == 'CNY':
                vat_diff_amount = (sale_amount - purchase_cost - stock_cost) / 1.13 * 0.13

            profit_amount = real_sale_amount - purchase_cost - stock_cost - other_cost - vat_diff_amount - sale_commission_amount + back_tax_amount

            one.shoukuan_amount = one.sale_invoice_id.amount_total - one.sale_invoice_id.residual_signed
            one.fukuan_amount = sum([i.amount_total - i.residual_signed for i in one.purchase_invoice_ids.filtered(
                lambda x: x.yjzy_type == 'purchase')])  # （采购发票line.合计金额 - 到期金额）

            budget_amount = one.fee_inner + one.fee_rmb1 + one.fee_rmb2 + one.get_budget_outer()  # + one.get_outer()
            budget_reset_amount = budget_amount - sum([x.company_currency_total_amount for x in one.expense_ids])
            print('-org1-', org_sale_amount)
            one.org_sale_amount = org_sale_amount
            one.org_real_sale_amount = org_real_sale_amount
            one.sale_amount = sale_amount
            one.real_sale_amount = real_sale_amount
            one.sale_commission_amount = sale_commission_amount
            one.stock_cost = stock_cost
            one.purchase_cost = purchase_cost
            one.other_cost = other_cost
            one.back_tax_amount = back_tax_amount
            one.back_tax_amount_org = back_tax_amount_org
            one.profit_amount = profit_amount
            one.fandian_amount = fandian_amount
            one.budget_amount = budget_amount
            one.budget_reset_amount = budget_reset_amount
            one.gold_sample_state = gold_sample_state
            one.ps_state = ps_state

            ###profit_ratio_base = (one.sale_amount - one.get_outer())
            one.profit_ratio = one.sale_amount != 0.0 and one.profit_amount / one.sale_amount or 0
            one.purchase_invoice_ids2 = one.purchase_invoice_ids.filtered(lambda x: x.yjzy_type == 'purchase')
            print('transport', ps_state)

            # fee_inner = 0.0
            # fee_rmb1 = 0.0
            # fee_rmb2 = 0.0
            # fee_outer = 0.0
            # fee_export_insurance =0.0
            # fee_other = 0.0
            # for x in one.line_ids:
            #     fee_inner +=  x.sol_id.order_id.amount_total and x.sol_id.price_unit / x.sol_id.order_id.amount_total * x.sol_id.order_id.fee_inner * x.plan_qty
            #     fee_rmb1 += x.sol_id.order_id.amount_total and x.sol_id.price_unit / x.sol_id.order_id.amount_total * x.sol_id.order_id.fee_rmb1 * x.plan_qty
            #     fee_rmb2 += x.sol_id.order_id.amount_total and x.sol_id.price_unit / x.sol_id.order_id.amount_total * x.sol_id.order_id.fee_rmb2 * x.plan_qty
            #     fee_outer += x.sol_id.order_id.amount_total and x.sol_id.price_unit / x.sol_id.order_id.amount_total * x.sol_id.order_id.fee_outer * x.plan_qty
            #     fee_export_insurance += x.sol_id.order_id.amount_total and x.sol_id.price_unit / x.sol_id.order_id.amount_total * x.sol_id.order_id.fee_export_insurance * x.plan_qty
            #     fee_other += x.sol_id.order_id.amount_total and x.sol_id.price_unit / x.sol_id.order_id.amount_total * x.sol_id.order_id.fee_other * x.plan_qty
            # one.fee_inner_so = fee_inner
            # one.fee_rmb1_so = fee_rmb1
            # one.fee_rmb2_so = fee_rmb2
            # one.fee_other_so = fee_outer
            # one.fee_export_insurance_so = fee_export_insurance
            # one.fee_other_so = fee_other

            # one.fee_inner = fee_inner
            # one.fee_rmb1 = fee_rmb1
            # one.fee_rmb2 = fee_rmb2
            # one.fee_other = fee_outer
            # one.fee_export_insurance = fee_export_insurance
            # one.fee_other = fee_other
            #
            # print('---fee_inner_test---', fee_inner, fee_rmb1)

    def _get_qingguan(self):
        # akiny新增 计算清关总量
        for one in self:
            qingguan_lines = one.qingguan_line_ids
            if qingguan_lines:
                one.qingguan_amount = sum([x.sub_total for x in qingguan_lines])
                one.qingguan_qty_total = sum([x.qty for x in qingguan_lines])
                one.qingguan_case_qty_total = sum([x.package_qty for x in qingguan_lines])
                one.qingguan_net_weight_total = sum([x.net_weight for x in qingguan_lines])
                one.qingguan_gross_wtight_total = sum([x.shiji_weight for x in qingguan_lines])
                one.qingguan_volume_total = sum([x.shiji_volume for x in qingguan_lines])

    def _get_fee_inner_so(self):
        fee_inner = 0.0
        for one in self:
            if one.line_ids:
                for x in one.line_ids:
                    fee_inner += x.sol_id.order_id.amount_total and x.sol_id.price_unit / x.sol_id.order_id.amount_total * x.sol_id.order_id.fee_inner * x.plan_qty
                one.fee_inner_so = fee_inner

    def _get_fee_rmb1_so(self):
        fee_rmb1 = 0.0
        for one in self:
            if one.line_ids:
                for x in one.line_ids:
                    fee_rmb1 += x.sol_id.order_id.amount_total and x.sol_id.price_unit / x.sol_id.order_id.amount_total * x.sol_id.order_id.fee_rmb1 * x.plan_qty
                one.fee_rmb1_so = fee_rmb1

    def _get_fee_rmb2_so(self):
        fee_rmb2 = 0.0
        for one in self:
            if one.line_ids:
                for x in one.line_ids:
                    fee_rmb2 += x.sol_id.order_id.amount_total and x.sol_id.price_unit / x.sol_id.order_id.amount_total * x.sol_id.order_id.fee_rmb2 * x.plan_qty
                one.fee_rmb2_so = fee_rmb2

    def _get_fee_outer_so(self):
        fee_outer = 0.0
        for one in self:
            if one.line_ids:
                for x in one.line_ids:
                    fee_outer += x.sol_id.order_id.amount_total and x.sol_id.price_unit / x.sol_id.order_id.amount_total * x.sol_id.order_id.fee_outer * x.plan_qty
                one.fee_outer_so = fee_outer

    def _get_fee_export_insurance_so(self):
        fee_export_insurance = 0.0
        for one in self:
            if one.line_ids:
                for x in one.line_ids:
                    fee_export_insurance += x.sol_id.order_id.amount_total and x.sol_id.price_unit / x.sol_id.order_id.amount_total * x.sol_id.order_id.fee_export_insurance * x.plan_qty
                one.fee_export_insurance_so = fee_export_insurance

    def _get_fee_other_so(self):
        fee_other = 0.0
        for one in self:
            if one.line_ids:
                for x in one.line_ids:
                    fee_other += x.sol_id.order_id.amount_total and x.sol_id.price_unit / x.sol_id.order_id.amount_total * x.sol_id.order_id.fee_other * x.plan_qty
                one.fee_other_so = fee_other

    def sum_other(self):
        self.ensure_one()
        return sum([self.fee_inner,
                    self.fee_rmb1,
                    self.fee_rmb2,
                    self.outer_currency_id.compute(self.fee_outer, self.company_currency_id),
                    self.export_insurance_currency_id.compute(self.fee_export_insurance, self.company_currency_id),
                    self.other_currency_id.compute(self.fee_other, self.company_currency_id), ])

    def get_outer(self):
        self.ensure_one()
        return sum([self.outer_currency_id.compute(self.fee_outer, self.company_currency_id),
                    self.export_insurance_currency_id.compute(self.fee_export_insurance, self.company_currency_id),
                    self.other_currency_id.compute(self.fee_other, self.company_currency_id), ])

    def get_budget_outer(self):
        self.ensure_one()
        return sum([self.outer_currency_id.compute(self.fee_outer, self.company_currency_id),
                    self.other_currency_id.compute(self.fee_other, self.company_currency_id), ])

    def _get_sale_amount(self, lines):
        """
        return:  org_sale_amount:sale_currency   sale_amount: third_currency
        line: sale_amount：company_currency_id， org_currency_sale_amount：sale_currency_id
        """
        org_sale_amount = sum(x.org_currency_sale_amount for x in lines)
        current_date_rate = self.current_date_rate
        if self.company_id.is_current_date_rate:
            sale_amount = org_sale_amount * current_date_rate
            if self.fee_outer_need:
                sale_amount += self.fee_outer * self.current_date_rate
        else:
            sale_amount = sum(x.company_currency_id.compute(x.sale_amount, self.third_currency_id) for x in lines)
            if self.fee_outer_need:
                sale_amount += self.outer_currency_id.compute(self.fee_outer, self.third_currency_id)

        print('-org-', org_sale_amount)
        if self.fee_outer_need:
            org_sale_amount += self.outer_currency_id.compute(self.fee_outer, self.sale_currency_id)

        return org_sale_amount, sale_amount

    def _get_sale_commission(self, sale_amount):
        sale_commission_ratio = float(
            self.env['ir.config_parameter'].sudo().get_param('addons_yjzy.sale_commission', '0.015'))
        return sale_commission_ratio, sale_amount * sale_commission_ratio

    def _get_other_cost(self):
        current_date_rate = self.current_date_rate
        other_cost = 0.0
        if self.company_id.is_current_date_rate:
            other_cost = self.fee_inner + self.fee_rmb1 + self.fee_rmb2 + (
                    self.fee_outer + self.fee_export_insurance + self.fee_other) * current_date_rate
        else:
            other_cost = sum([self.fee_inner, self.fee_rmb1, self.fee_rmb2,
                              self.outer_currency_id.compute(self.fee_outer, self.company_currency_id),
                              self.export_insurance_currency_id.compute(self.fee_export_insurance,
                                                                        self.company_currency_id),
                              self.other_currency_id.compute(self.fee_other, self.company_currency_id),
                              ])
        return other_cost

    @api.depends('hsname_ids', 'hsname_ids.amount2', 'pack_line_ids.no_ciq_amount')
    def compute_ciq_amount(self):
        for one in self:
            pack_lines = one.pack_line_ids
            one.ciq_amount = sum([x.amount2 for x in one.hsname_ids])
            one.ciq_amount_new = sum([x.amount2 for x in one.hsname_ids])
            one.no_ciq_amount = sum([x.no_ciq_amount for x in pack_lines])

    @api.depends('sale_currency_id', 'currency_id', 'date')
    def compute_exchange_rate(self):
        for one in self:
            date = one.date or fields.date.today()
            currench_obj = self.env['res.currency'].with_context(date=date)
            exchange_rate = 0
            if one.company_currency_id and one.sale_currency_id:
                exchange_rate = currench_obj._get_conversion_rate(one.sale_currency_id, one.company_currency_id)
            one.exchange_rate = exchange_rate

    @api.depends('sale_invoice_id', 'purchase_invoice_ids', 'back_tax_invoice_id')
    def compute_invoice_amount(self):
        for one in self:
            sale_invoice = one.sale_invoice_id.filtered(lambda x: x.state not in ['draft', 'cancel'])
            purchase_invoices = one.purchase_invoice_ids.filtered(
                lambda x: x.yjzy_type == 'purchase' and x.state not in ['draft', 'cancel'])
            back_tax_invoice = one.back_tax_invoice_id.filtered(lambda x: x.state not in ['draft', 'cancel'])

            # one.sale_invoice_total = sale_invoice.amount_total
            # one.purhcase_invoice_total = sum([x.amount_total for x in purchase_invoices])
            # one.back_tax_invoice_total = back_tax_invoice.amount_total
            # one.sale_invoice_paid = sale_invoice.amount_total-sale_invoice.residual_signed #akiny
            # one.purhcase_invoice_paid = sum([x.amount_total for x in purchase_invoices])-sum([x.residual_signed for x in purchase_invoices])
            # one.back_tax_invoice_paid = back_tax_invoice.amount_total-back_tax_invoice.residual_signed
            # one.sale_invoice_balance = sale_invoice.residual_signed
            # one.purhcase_invoice_balance = sum([x.residual_signed for x in purchase_invoices])
            # one.back_tax_invoice_balance = back_tax_invoice.residual_signed

            one.all_purchase_invoice_fill = all([x.date_finish for x in purchase_invoices])

    # @api.depends('line_ids.plan_qty','line_ids','current_date_rate')
    # def amount_all(self):
    #     """
    #     Compute the total amounts of the SO.
    #     """
    #     for one in self:
    #         org_sale_amount_new = 0
    #         for line in one.line_ids:
    #             org_sale_amount_new += line.org_currency_sale_amount
    #         one.update({
    #             'org_sale_amount_new': one.sale_currency_id.round(org_sale_amount_new),
    #         })

    @api.depends('line_ids', 'line_ids.plan_qty', 'current_date_rate', 'line_ids.org_currency_sale_amount_new',
                 'purchase_invoice_total_new', 'stage_id', 'second_state',
                 'sale_invoice_total_new', 'line_ids.org_currency_sale_amount_origin_new', 'hsname_ids',
                 'hsname_ids.amount', 'hsname_ids.actual_amount', 'current_date_rate',
                 'hsname_ids.purchase_amount2', 'hsname_ids.purchase_amount', 'line_ids.purchase_cost_new')
    def amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for one in self:
            sale_invoice_total_new = one.sale_invoice_total_new
            purchase_invoice_total_new = one.purchase_invoice_total_new
            current_date_rate = one.current_date_rate
            line_ids = one.line_ids
            hsname_ids = one.hsname_ids
            org_sale_amount_new = sum(x.org_currency_sale_amount for x in line_ids)
            org_purchase_amount_new = sum(x.purchase_cost_new for x in line_ids)
            org_sale_amount_new_origin = sum(x.org_currency_sale_amount_origin for x in line_ids)
            org_sale_amount_new_discount = org_sale_amount_new_origin - org_sale_amount_new
            if line_ids:
                if hsname_ids:
                    org_real_sale_amount_new = sum([x.amount for x in hsname_ids])
                    org_hsname_actual_amount = sum([x.actual_amount for x in hsname_ids])
                    diff_real_sale_hsmame_actual_amount = sale_invoice_total_new - org_hsname_actual_amount

                    org_real_purchase_amount_new = sum([x.purchase_amount for x in hsname_ids])
                    purchase_hsname_actual_cost_total = sum(x.purchase_amount2 for x in hsname_ids)
                    diff_real_purchase_hsname_actual_amount = purchase_invoice_total_new - purchase_hsname_actual_cost_total
                    if one.company_id.is_current_date_rate:
                        real_sale_amount_cny = org_real_sale_amount_new * current_date_rate
                        hsname_actual_amount_cny = org_hsname_actual_amount * current_date_rate
                    else:
                        real_sale_amount_cny = one.third_currency_id and one.sale_currency_id.compute(
                            org_real_sale_amount_new,
                            one.third_currency_id) or 0
                        hsname_actual_amount_cny = one.third_currency_id and one.sale_currency_id.compute(
                            org_hsname_actual_amount,
                            one.third_currency_id) or 0
                else:
                    org_real_sale_amount_new = org_sale_amount_new
                    org_hsname_actual_amount = org_sale_amount_new
                    diff_real_sale_hsmame_actual_amount = sale_invoice_total_new - org_hsname_actual_amount
                    org_real_purchase_amount_new = org_purchase_amount_new
                    purchase_hsname_actual_cost_total = org_purchase_amount_new
                    diff_real_purchase_hsname_actual_amount = purchase_invoice_total_new - purchase_hsname_actual_cost_total
                    if one.company_id.is_current_date_rate:
                        real_sale_amount_cny = org_real_sale_amount_new * current_date_rate
                        hsname_actual_amount_cny = org_hsname_actual_amount * current_date_rate
                    else:
                        real_sale_amount_cny = one.third_currency_id and one.sale_currency_id.compute(
                            org_real_sale_amount_new,
                            one.third_currency_id) or 0
                        hsname_actual_amount_cny = one.third_currency_id and one.sale_currency_id.compute(
                            org_hsname_actual_amount,
                            one.third_currency_id) or 0
                    print('diff_real_sale_hsmame_actual_amount_akiny', diff_real_sale_hsmame_actual_amount)

                one.diff_real_sale_hsmame_actual_amount = diff_real_sale_hsmame_actual_amount
                one.org_sale_amount_new_origin = org_sale_amount_new_origin
                one.org_sale_amount_new = org_sale_amount_new
                one.org_hsname_actual_amount = org_hsname_actual_amount
                one.org_real_sale_amount_new = org_real_sale_amount_new
                one.real_sale_amount_cny = real_sale_amount_cny
                one.hsname_actual_amount_cny = hsname_actual_amount_cny
                one.org_sale_amount_new_discount = org_sale_amount_new_discount

                one.org_real_purchase_amount_new = org_real_purchase_amount_new
                one.purchase_hsname_actual_cost_total = purchase_hsname_actual_cost_total
                one.diff_real_purchase_hsname_actual_amount = diff_real_purchase_hsname_actual_amount

    @api.depends('line_ids.plan_qty', 'line_ids', 'current_date_rate', 'state', 'fee_inner', 'fee_rmb1', 'fee_rmb2',
                 'fee_outer')
    def _sale_purchase_amount(self):
        """
        Compute the total amounts of the SO.
        """
        for one in self:
            org_sale_amount = sum(x.org_currency_sale_amount for x in one.line_ids)
            purchase_cost_total = sum(x.purchase_cost for x in one.line_ids)

            one.update({
                'org_sale_amount_new': one.sale_currency_id.round(org_sale_amount),
                'purchase_cost_total': one.sale_currency_id.round(purchase_cost_total),

            })

    # 加上额外账单
    @api.depends('sale_invoice_id.amount_total', 'sale_invoice_id.residual_signed', 'sale_invoice_id.yjzy_total',
                 'sale_invoice_id.yjzy_residual')
    def sale_invoice_amount(self):
        for one in self:
            sale_invoice = one.sale_invoice_id.filtered(lambda x: x.state not in ['draft', 'cancel'])
            sale_invoice_total = sale_invoice.yjzy_total
            sale_invoice_balance = sale_invoice.yjzy_residual
            sale_invoice_paid = sale_invoice_total - sale_invoice_balance  # akiny
            one.update({
                'sale_invoice_total_new': one.sale_currency_id.round(sale_invoice_total),
                'sale_invoice_paid_new': one.sale_currency_id.round(sale_invoice_paid),
                'sale_invoice_balance_new': one.sale_currency_id.round(sale_invoice_balance),
                'sale_invoice_total': sale_invoice_total,
                'sale_invoice_paid': sale_invoice_paid,
                'sale_invoice_balance': sale_invoice_balance
            })

    # 加入了额外账单的统计
    @api.depends('purchase_invoice_ids.amount_total', 'purchase_invoice_ids.residual_signed',
                 'back_tax_invoice_id.yjzy_total', 'back_tax_invoice_id.yjzy_residual')
    def purchase_invoice_amount(self):
        for one in self:
            purchase_invoices = one.purchase_invoice_ids.filtered(
                lambda x: x.yjzy_type == 'purchase' and x.state not in ['draft', 'cancel'])
            purchase_invoice_total = sum([x.yjzy_total for x in purchase_invoices])
            purchase_invoice_balance = sum([x.yjzy_residual for x in purchase_invoices])
            purchase_invoice_paid = purchase_invoice_total - purchase_invoice_balance
            one.update({
                'purchase_invoice_total_new': one.sale_currency_id.round(purchase_invoice_total),
                'purchase_invoice_paid_new': one.sale_currency_id.round(purchase_invoice_paid),
                'purchase_invoice_balance_new': one.sale_currency_id.round(purchase_invoice_balance),
                'purhcase_invoice_total': purchase_invoice_total,
                'purhcase_invoice_paid': purchase_invoice_paid,
                'purhcase_invoice_balance': purchase_invoice_balance
            })

    @api.depends('back_tax_invoice_id.amount_total', 'back_tax_invoice_id.residual_signed',
                 'back_tax_invoice_id.yjzy_total', 'back_tax_invoice_id.yjzy_residual')
    def back_tax_invoice_amount(self):
        for one in self:
            back_tax_invoice = one.back_tax_invoice_id.filtered(lambda x: x.state not in ['draft', 'cancel'])
            back_tax_invoice_total = back_tax_invoice.yjzy_total
            back_tax_invoice_balance = back_tax_invoice.yjzy_residual
            back_tax_invoice_paid = back_tax_invoice_total - back_tax_invoice_balance
            one.update({
                'back_tax_invoice_total_new': one.sale_currency_id.round(back_tax_invoice_total),
                'back_tax_invoice_balance_new': one.sale_currency_id.round(back_tax_invoice_balance),
                'back_tax_invoice_paid_new': one.sale_currency_id.round(back_tax_invoice_paid),
                'back_tax_invoice_total': back_tax_invoice_total,
                'back_tax_invoice_balance': back_tax_invoice_balance,
                'back_tax_invoice_paid': back_tax_invoice_paid
            })

    # 供应商交单日期审批状态
    def compute_date_purchase_finish_state(self):
        for one in self:

            print('-采购发票-', one.purchase_invoice_ids)
            if all([x.purchase_date_finish_state == 'draft' for x in one.purchase_invoice_ids]):
                date_purchase_finish_state = 'draft'
            elif all([x.purchase_date_finish_state == 'done' for x in one.purchase_invoice_ids]):
                date_purchase_finish_state = 'done'
            elif any([x.purchase_date_finish_state == 'submit' for x in one.purchase_invoice_ids]):
                date_purchase_finish_state = 'submit'
            else:
                date_purchase_finish_state = 'draft'
            one.date_purchase_finish_state = date_purchase_finish_state

    # @api.depends('date_out_in','date_in','date_ship','date_customer_finish','all_purchase_invoice_fill')
    # def _compute_date_all_state(self):
    #     for one in self:
    #         # 日期填写状态计算 akiny
    #         today = datetime.now()
    #         date_all_state = 'un_done'
    #         if one.date_out_in_state != 'done':
    #             if one.approve_date and one.approve_date >= (today - relativedelta(days=15)).strftime('%Y-%m-%d 00:00:00'):
    #                 date_all_state = 'normal_no_date_out_in'
    #             else:
    #                 date_all_state = 'unnormal_no_date_out_in'
    #         else:
    #             if one.date_ship_state =='done' and one.date_customer_finish_state == 'done' and one.date_purchase_finish_state == 'done':
    #                 date_all_state = 'done'
    #             else:
    #                 if one.date_out_in and one.approve_date < (today - relativedelta(days=30)).strftime('%Y-%m-%d 00:00:00'):
    #                     date_all_state = 'abnormal'
    #                 else:
    #                     date_all_state = 'un_done'
    #         one.date_all_state = date_all_state

    # # 计算时间的有用
    # @api.depends('date_out_in', 'date_in', 'date_ship', 'date_customer_finish', 'all_purchase_invoice_fill','date_ship_state','date_out_in_state','date_customer_finish_state','date_purchase_finish_state')
    # def compute_date_all_state_old(self):
    #     date_all_state = '30_un_done'
    #     for one in self:
    #         # 日期填写状态计算 akiny
    #
    #         if one.date_out_in_state == 'draft':
    #             date_all_state = '20_no_date_out_in'
    #         else:
    #             if one.date_out_in_state == 'done' and one.date_ship_state == 'done' and one.date_customer_finish_state == 'done' and one.date_purchase_finish_state == 'done':
    #                 date_all_state = '40_done'
    #             else:
    #                 date_all_state = '30_un_done'
    #         one.date_all_state = date_all_state

    @api.depends('all_invoice_ids', 'all_invoice_ids.state', 'date_out_in', 'date_in', 'date_ship',
                 'date_customer_finish', 'date_delivered_id_done')
    def compute_date_all_state(self):
        for one in self:
            all_invoice_ids = one.all_invoice_ids
            if one.date_out_in and len(all_invoice_ids.filtered(lambda x: x.state != 'paid')) == 0:
                date_all_state = '50_payable_done'
            else:
                if one.date_out_in == False:
                    date_all_state = '20_no_date_out_in'
                elif one.date_delivered_id_done == False and one.date_out_in != False:
                    date_all_state = '23_no_date_delivered'
                elif one.date_ship == False and one.date_out_in != False and one.date_delivered_id_done != False:
                    date_all_state = '25_no_date_ship'
                elif one.date_customer_finish == False and one.date_ship != False and one.date_out_in != False and one.date_delivered_id_done != False:
                    date_all_state = '27_no_date_finish'
                else:
                    # if one.date_out_in != False and one.date_ship != False and one.date_customer_finish != False and one.date_delivered_id_done == True:
                    #     date_all_state = '40_done'
                    # else:
                    date_all_state = '30_un_done'
            one.date_all_state = date_all_state

    # @api.depends('date_out_in', 'date_in', 'date_ship', 'date_customer_finish', 'all_purchase_invoice_fill','purchase_invoice_ids','purchase_invoice_ids.date_finish',
    #              'date_ship_state', 'date_out_in_state', 'date_customer_finish_state', 'date_purchase_finish_state','second_state')
    # def compute_date_all_state_new(self):
    #     for one in self:
    #         # 日期填写状态计算 akiny
    #         if one.date_out_in_state == 'submit' or one.date_ship_state == 'submit' \
    #                 or one.date_customer_finish_state == 'submit' or one.date_purchase_finish_state == 'submit':
    #             date_all_state = '10_date_approving'
    #         else:
    #             if not one.date_out_in or not one.is_date_out_in:
    #                 date_all_state = '20_no_date_out_in'
    #             else:
    #                 if one.date_out_in and one.date_ship and one.date_customer_finish and len(one.purchase_invoice_ids) == len(one.purchase_invoice_ids.filtered(lambda x:x.date_finish != False)) and one.second_state in ['30','40','50']:
    #                     date_all_state = '40_done'
    #                 else:
    #                     date_all_state = '30_un_done'
    #         one.date_all_state = date_all_state

    # 失效
    @api.depends('date_out_in', 'date_in', 'date_ship', 'date_customer_finish', 'all_purchase_invoice_fill', 'state')
    def update_state_type(self):
        for one in self:
            state_type = one.state_type
            date_out_in = one.date_out_in
            date_ship = one.date_ship
            date_customer_finish = one.date_customer_finish
            all_purchase_invoice_fill = one.all_purchase_invoice_fill
            today = datetime.now()
            state = one.state
            if state in ('invoiced', 'verifying'):
                if date_out_in and date_ship and date_customer_finish and all_purchase_invoice_fill:
                    state_type = 'finish_date'
                    state = 'invoiced'
                    if one.sale_invoice_balance_new == 0 and one.purchase_invoice_balance_new == 0 and one.back_tax_invoice_balance_new == 0:
                        state = 'verifying'
                        state_type = 'write_off'
                    else:
                        if date_out_in < (today - relativedelta(days=185)).strftime('%Y-%m-%d 00:00:00'):
                            state = 'verifying'
                            state_type = 'abnormal'
                else:
                    if not date_out_in:
                        state = 'invoiced'
                        state_type = 'no_delivery'
                    else:
                        if one.approve_date and one.approve_date < (today - relativedelta(days=30)).strftime(
                                '%Y-%m-%d 00:00:00'):
                            state_type = 'abnormal_date'
                            state = 'invoiced'
            print('--状态更新-', state_type, one, one.state)
            one.state_type = state_type
            one.state = state

    # @api.depends('so_ids','incoterm','payment_term_id','include_tax','line_ids')
    def compute_same(self):
        for one in self:
            same_incoterm = one.so_ids.mapped('incoterm')
            same_payment_term = one.so_ids.mapped('payment_term_id')
            same_currency = one.so_ids.mapped('sale_currency_id')
            same_include_tax = one.so_ids.mapped('include_tax')
            print('-testincoterm-', same_incoterm)
            if len(same_incoterm) == 1 and one.incoterm == same_incoterm[0]:
                is_same_incoterm = True
            else:
                is_same_incoterm = False
            if len(same_payment_term) == 1 and one.payment_term_id == same_payment_term[0]:
                is_same_payment_term = True
            else:
                is_same_payment_term = False
            if len(same_currency) == 1 and one.sale_currency_id == same_currency[0]:
                is_same_currency = True
            else:
                is_same_currency = False
            if len(set(same_include_tax)) == 1 and one.include_tax == same_include_tax[0]:
                is_same_include_tax = True
            else:
                is_same_include_tax = False
            one.same_incoterm = is_same_incoterm
            one.same_payment_term = is_same_payment_term
            one.same_currency = is_same_currency
            one.same_include_tax = is_same_include_tax

    @api.depends('all_invoice_ids', 'all_invoice_ids.state', 'all_invoice_ids.residual_signed', 'sale_invoice_id',
                 'sale_invoice_id.state', 'sale_invoice_id.residual_signed', 'purchase_invoice_ids',
                 'purchase_invoice_ids.state')
    def compute_invoice_paid_state(self):
        for one in self:
            invoice_paid_state = 'e'
            back_tax_invoice_id = one.back_tax_invoice_id
            line_purchase_invoice_count = len(
                one.purchase_invoice_ids.filtered(lambda x: x.state not in ['draft', 'cancel']))
            line_purchase_invoice_ids = one.purchase_invoice_ids
            sale_invoice_id = one.sale_invoice_id
            if not back_tax_invoice_id:
                if line_purchase_invoice_count > 0 and sale_invoice_id and sale_invoice_id.state not in (
                        'draft', 'cancel'):
                    if all([x.state == 'paid' for x in line_purchase_invoice_ids]) and sale_invoice_id.state == 'paid':
                        invoice_paid_state = 'a_paid'
                    else:
                        if not all([x.state == 'paid' for x in
                                    one.purchase_invoice_ids]) and sale_invoice_id.state == 'paid':
                            invoice_paid_state = 'c'
                        if all([x.state == 'paid' for x in
                                one.purchase_invoice_ids]) and sale_invoice_id.state != 'paid':
                            invoice_paid_state = 'b'
                        if not all([x.state == 'paid' for x in
                                    one.purchase_invoice_ids]) and sale_invoice_id.state != 'paid':
                            invoice_paid_state = 'd_no_paid'
                    one.invoice_paid_state = invoice_paid_state
                else:
                    one.invoice_paid_state = 'e'
            else:
                if line_purchase_invoice_count > 0 and sale_invoice_id and sale_invoice_id.state not in (
                        'draft', 'cancel') and back_tax_invoice_id not in ('draft', 'cancel'):
                    if all([x.state == 'paid' for x in
                            line_purchase_invoice_ids]) and sale_invoice_id.state == 'paid' and back_tax_invoice_id.state == 'paid':
                        invoice_paid_state = 'a_paid'
                    else:
                        if not all([x.state == 'paid' for x in
                                    one.purchase_invoice_ids]) and sale_invoice_id.state == 'paid' and back_tax_invoice_id.state == 'paid':
                            invoice_paid_state = 'c'
                        if all([x.state == 'paid' for x in one.purchase_invoice_ids]) and (
                                sale_invoice_id.state != 'paid' or back_tax_invoice_id.state != 'paid'):
                            invoice_paid_state = 'b'
                        if not all([x.state == 'paid' for x in one.purchase_invoice_ids]) and (
                                sale_invoice_id.state != 'paid' or back_tax_invoice_id.state != 'paid'):
                            invoice_paid_state = 'd_no_paid'
                    one.invoice_paid_state = invoice_paid_state
                else:
                    one.invoice_paid_state = 'e'
        # for one in self:
        #     invoice_paid_state = 'e'
        #     line_purchase_invoice_count = len(one.purchase_invoice_ids.filtered(lambda x: x.state not in ['draft','cancel']))
        #     line_count_paid = len(one.all_invoice_ids.filtered(lambda x: x.state == 'paid'))
        #     sale_invoice_id = one.sale_invoice_id
        #     line_purchase_invoice_paid_count = len(one.purchase_invoice_ids.filtered(lambda x: x.state == 'paid'))
        #     if line_purchase_invoice_count > 0 and sale_invoice_id and sale_invoice_id.state not in ('draft','cancel'):
        #         if line_count_paid > 0:
        #             if line_purchase_invoice_paid_count >0 and sale_invoice_id.state == 'paid':
        #                 invoice_paid_state = 'b'
        #             elif line_purchase_invoice_paid_count == 0 and sale_invoice_id.state == 'open':
        #                 invoice_paid_state = 'c'
        #             elif line_purchase_invoice_paid_count == 0 and sale_invoice_id.state == 'paid':
        #                 invoice_paid_state = 'a_paid'
        #         else:
        #             invoice_paid_state = 'd_no_paid'
        #         one.invoice_paid_state = invoice_paid_state
        #     else:
        #         one.invoice_paid_state = 'e'

    # @api.model
    # def _default_fee_inner(self):
    #     fee_inner = 0.0
    #     for x in self.line_ids:
    #         fee_inner += x.sol_id.order_id.amount_total and x.sol_id.price_unit / x.sol_id.order_id.amount_total * x.sol_id.order_id.fee_inner * x.plan_qty
    #     print('---default_inner--',fee_inner)
    #
    #     if fee_inner > 0:
    #         return fee_inner
    # qq注意额外账单加上后，怎么办
    # @api.depends('all_invoice_ids', 'all_invoice_ids.state', 'all_invoice_ids.residual_signed', 'sale_invoice_id',
    #              'sale_invoice_id.state', 'sale_invoice_id.residual_signed', 'purchase_invoice_ids',
    #              'purchase_invoice_ids.state', )
    # def compute_second_state(self):
    #     for one in self:
    #         second_state = '10'
    #         back_tax_invoice_id = one.back_tax_invoice_id
    #         line_purchase_invoice_count = len(
    #             one.purchase_invoice_ids.filtered(lambda x: x.state not in ['draft', 'cancel']))
    #         line_purchase_invoice_ids = one.purchase_invoice_ids
    #         sale_invoice_id = one.sale_invoice_id
    #         today = datetime.now()
    #         # if not back_tax_invoice_id:
    #         #     if line_purchase_invoice_count > 0 and sale_invoice_id and sale_invoice_id.state not in (
    #         #     'draft', 'cancel'):
    #         #         if all([x.state == 'paid' for x in line_purchase_invoice_ids]) and sale_invoice_id.state == 'paid':
    #         #             second_state = '60'
    #         #         else:
    #         #             if sale_invoice_id.residual_times_new >30:
    #         #                 second_state = '70'
    #         #             else:
    #         #                 if not all([x.state == 'paid' for x in
    #         #                             one.purchase_invoice_ids]) and sale_invoice_id.state == 'paid':
    #         #                     second_state = '40'
    #         #                 if all([x.state == 'paid' for x in
    #         #                         one.purchase_invoice_ids]) and sale_invoice_id.state != 'paid':
    #         #                     second_state = '50'
    #         #                 if not all([x.state == 'paid' for x in
    #         #                             one.purchase_invoice_ids]) and sale_invoice_id.state != 'paid':
    #         #                     second_state = '30'
    #         #         one.second_state = second_state
    #         #     else:
    #         #         one.invoice_paid_state = 'e'
    #         # else:
    #         if line_purchase_invoice_count > 0 and sale_invoice_id and sale_invoice_id.state not in (
    #         'draft', 'cancel') and (back_tax_invoice_id not in ('draft', 'cancel') or not back_tax_invoice_id):
    #             if all([x.state == 'paid' for x in
    #                     line_purchase_invoice_ids]) and sale_invoice_id.state == 'paid' and (back_tax_invoice_id.state == 'paid' or not back_tax_invoice_id):
    #                 second_state = '60'
    #             else:
    #                 if (sale_invoice_id.state == 'open' and sale_invoice_id.residual_times_new >30) or \
    #                         (back_tax_invoice_id and back_tax_invoice_id.state == 'open' and back_tax_invoice_id.residual_times_new > 30):
    #                     second_state = '70'
    #                 else:
    #                     if not all([x.state == 'paid' for x in
    #                                 one.purchase_invoice_ids]) and sale_invoice_id.state == 'paid' and (back_tax_invoice_id.state == 'paid' or not back_tax_invoice_id):
    #                         second_state = '40'
    #                     if all([x.state == 'paid' for x in one.purchase_invoice_ids]) and (
    #                             sale_invoice_id.state != 'paid' or (back_tax_invoice_id and back_tax_invoice_id.state != 'paid')):
    #                         second_state = '50'
    #                     if not all([x.state == 'paid' for x in one.purchase_invoice_ids]) and (
    #                             sale_invoice_id.state != 'paid' or (back_tax_invoice_id and back_tax_invoice_id.state != 'paid')):
    #                         second_state = '30'
    #         else:
    #             if one.approve_date:
    #                 if one.approve_date < (today - relativedelta(days=30)).strftime(
    #                         '%Y-%m-%d 00:00:00'):
    #                     second_state = '20'
    #                 else:
    #                     second_state = '10'
    #         one.second_state = second_state
    # qq1  就这个一个就可以了
    @api.depends('all_invoice_ids', 'all_invoice_ids.state', 'all_invoice_ids.residual_signed', 'sale_invoice_id',
                 'sale_invoice_id.state', 'sale_invoice_id.residual_signed', 'purchase_invoice_ids',
                 'purchase_invoice_ids.residual_signed',
                 'purchase_invoice_ids.state', 'sale_invoice_balance_new', 'purchase_invoice_balance_new',
                 'back_tax_invoice_balance_new', 'state')
    def compute_second_state(self):
        for one in self:
            back_tax_invoice_id = one.back_tax_invoice_id
            line_purchase_invoice_count = len(
                one.purchase_invoice_ids.filtered(lambda x: x.state not in ['draft', 'cancel']))
            line_purchase_invoice_ids = one.purchase_invoice_ids
            sale_invoice_id = one.sale_invoice_id
            second_state = '10'
            sale_invoice_balance = one.sale_invoice_balance_new
            purchase_invoice_balance = one.purchase_invoice_balance_new
            back_tax_invoice_balance = one.back_tax_invoice_balance_new
            stage_id = one.stage_id

            today = datetime.now()
            # 未发货，开始发货，待核销，已核销
            if one.state in ('invoiced', 'verifying', 'abnormal'):
                if sale_invoice_balance == 0 and purchase_invoice_balance == 0 and back_tax_invoice_balance == 0:
                    stage_id = self._stage_find(domain=[('code', '=', '007')])
                    second_state = '60'
                else:
                    if (sale_invoice_balance != 0 and sale_invoice_id.residual_times_new > 30) or \
                            (back_tax_invoice_balance != 0 and back_tax_invoice_id.residual_times_new > 30):
                        second_state = '70'
                        stage_id = self._stage_find(domain=[('code', '=', '005')])
                    else:
                        if purchase_invoice_balance != 0 and sale_invoice_balance == 0 and back_tax_invoice_balance == 0:
                            second_state = '40'
                            stage_id = self._stage_find(domain=[('code', '=', '005')])
                        if purchase_invoice_balance == 0 and (
                                sale_invoice_balance != 0 or back_tax_invoice_balance != 0):
                            second_state = '50'
                            stage_id = self._stage_find(domain=[('code', '=', '005')])
                        if purchase_invoice_balance != 0 and (
                                sale_invoice_balance != 0 or back_tax_invoice_balance != 0):
                            second_state = '30'
                            stage_id = self._stage_find(domain=[('code', '=', '005')])
            else:
                if one.approve_date:
                    if one.approve_date < (today - relativedelta(days=7)).strftime(
                            '%Y-%m-%d 00:00:00'):
                        second_state = '20'
                    else:
                        second_state = '10'
                    stage_id = self._stage_find(domain=[('code', '=', '004')])
                else:
                    second_state = '09'
            one.second_state = second_state
            one.stage_id = stage_id

    def compute_border(self):
        for one in self:
            one.border_char = '|'

    @api.depends('date_out_in_state')
    def compute_date_out_in_first_state(self):
        for one in self:
            if one.date_out_in_state in ['draft', 'submit']:
                date_out_in_first_state = 'draft'
            else:
                date_out_in_first_state = 'done'
            one.date_out_in_first_state = date_out_in_first_state

    @api.model
    def _default_transport_stage(self):
        stage = self.env['transport.bill.stage']
        return stage.search([], limit=1)

    @api.depends('line_ids', 'line_ids.plan_qty', 'hsname_ids', 'hsname_ids.amount2')
    def compute_yjzy_invoice_amount_total(self):
        for one in self:
            usd_pool_id = False
            if one.state == 'approve':
                org_sale_amount = one.org_sale_amount
                ciq_amount = one.ciq_amount
                usd_pool = org_sale_amount - ciq_amount
                usd_pool_1 = org_sale_amount - ciq_amount
                usd_pool_id = self.env.ref('yjzy_extend.usd_pool_state1').id
            else:
                usd_pool_1 = 0
                usd_pool = 0
                usd_pool_id = False
            one.usd_pool = usd_pool
            one.usd_pool = usd_pool_1
            one.usd_pool_id = usd_pool_id

    # 814
    def _compute_po_include_tax(self):
        for one in self:
            po_include_tax = 'none'
            line_count = len(one.hsname_ids)
            line_count_include_tax = len(one.hsname_ids.filtered(lambda x: x.is_po_include_tax))
            if line_count_include_tax > 0:
                if line_count_include_tax == line_count:
                    po_include_tax = 'all'
                else:
                    po_include_tax = 'part'
            one.po_include_tax = po_include_tax

    @api.depends('qingguan_line_ids', 'qingguan_line_ids.sub_total_origin', 'qingguan_line_ids.sub_total')
    def compute_qingguan_amount_total(self):
        for one in self:
            qingguan_amount_total = 0
            qingguan_amount_total_origin = 0
            for line in one.qingguan_line_ids:
                qingguan_amount_total += line.sub_total
                qingguan_amount_total_origin += line.sub_total_origin

            one.qingguan_amount_total = qingguan_amount_total
            one.qingguan_amount_total_origin = qingguan_amount_total_origin

    @api.depends('purchase_invoice_ids', 'purchase_invoice_ids_new.date_finish')
    def compute_date_purchase_finish_is_done(self):
        for one in self:
            print('-采购发票-', one.purchase_invoice_ids)
            if all([x.date_finish != False for x in one.purchase_invoice_ids_new]):
                date_purchase_finish_is_done = True
            else:
                date_purchase_finish_is_done = False

            one.date_purchase_finish_is_done = date_purchase_finish_is_done

    @api.depends('purchase_invoice_ids', 'purchase_invoice_ids.supplier_delivery_date')
    def compute_date_delivered_id_done(self):
        for one in self:
            print('-采购发票-', one.purchase_invoice_ids)
            if all([x.supplier_delivery_date != False for x in one.purchase_invoice_ids]):
                date_delivered_id_done = True
            else:
                date_delivered_id_done = False

            one.date_delivered_id_done = date_delivered_id_done

    # 货币设置

    is_discount = fields.Boolean('是否折扣', default=False)
    qingguan_amount_total = fields.Monetary('清关合计金额', currency_field='sale_currency_id',
                                            compute=compute_qingguan_amount_total, store=True)
    qingguan_amount_total_origin = fields.Monetary('原清关合计金额', currency_field='sale_currency_id',
                                                   compute=compute_qingguan_amount_total, store=True)

    qingguan_container_no = fields.Text('CONTAINER NO')
    qingguan_seal_no = fields.Text('SEAL NO')
    # akiny 未加入

    qingguan_name = fields.Char(u'交单抬头')
    qingguan_address = fields.Text(u'交单地址')
    qingguan_phone = fields.Char(u'交单电话')
    po_include_tax = fields.Selection([('all', '全部含税'), ('part', '部分含税'), ('none', '不含税')], u'采购含税情况',
                                      compute=_compute_po_include_tax)  # 814
    usd_pool_id = fields.Many2one('usd.pool', u'美金池状态', compute=compute_yjzy_invoice_amount_total, store=True)
    usd_pool = fields.Float('美金池', compute=compute_yjzy_invoice_amount_total, store=True)
    usd_pool_1 = fields.Float('美金池1', compute=compute_yjzy_invoice_amount_total, store=True)
    # state2
    stage_id = fields.Many2one(
        'transport.bill.stage',
        default=_default_transport_stage, copy=False)
    border_char = fields.Char(u' ', compute=compute_border)
    sale_invoice_total_new = fields.Monetary(u'主应收原始金额', compute=sale_invoice_amount, store=True)  # ok
    sale_invoice_paid_new = fields.Monetary(u'已收销售发票', compute=sale_invoice_amount, store=True)
    sale_invoice_balance_new = fields.Monetary(u'主应收剩余金额', compute=sale_invoice_amount, store=True)  # ok
    purchase_invoice_total_new = fields.Monetary(u'主应付原始金额', compute=purchase_invoice_amount, store=True)  # ok
    purchase_invoice_paid_new = fields.Monetary(u'已付采购金额', compute=purchase_invoice_amount, store=True)
    purchase_invoice_balance_new = fields.Monetary(u'主应付剩余金额', compute=purchase_invoice_amount, store=True)  # ok
    back_tax_invoice_total_new = fields.Monetary(u'主退税原始金额', compute=back_tax_invoice_amount, store=True)  # ok
    back_tax_invoice_paid_new = fields.Monetary(u'已收退税金额', compute=back_tax_invoice_amount, store=True)
    back_tax_invoice_balance_new = fields.Monetary(u'主退税剩余金额', compute=back_tax_invoice_amount, store=True)  # ok

    purchase_cost_total = fields.Monetary(u'最原始采购金额', compute=_sale_purchase_amount, store=True)  # 13ok

    state_type = fields.Selection(
        [('no_delivery', '未开始'), ('wait_date', u'待完成相关日期'), ('finish_date', u'已完成相关日期'), ('abnormal_date', u'日期异常'),
         ('write_off', u'正常核销'), ('abnormal', u'异常核销')], u'状态类型', default='no_delivery', store=True,
        compute=update_state_type)
    # date_out_in_att = fields.Many2many('ir.attachment',string='进仓日附件')
    date_out_in_att = fields.One2many('trans.date.attachment', 'tb_id', domain=[('type', '=', 'date_out_in')],
                                      string='进仓日附件')
    date_out_in_att_count = fields.Integer('进仓日期附件数量', compute=compute_info)
    date_ship_att = fields.One2many('trans.date.attachment', 'tb_id', domain=[('type', '=', 'date_ship')],
                                    string='出运船日附件')
    date_ship_att_count = fields.Integer('出运船日期附件数量', compute=compute_info)
    date_customer_finish_att = fields.One2many('trans.date.attachment', 'tb_id',
                                               domain=[('type', '=', 'date_customer_finish')], string='客户交单日附件')
    date_customer_finish_att_count = fields.Integer('客户交单日期附件数量', compute=compute_info)
    date_out_in_first_state = fields.Selection([('draft', '发货时间待提交'),
                                                ('done', '发货时间已完成')], u'进仓日一级状态',
                                               compute=compute_date_out_in_first_state, store=True)
    date_out_in_state = fields.Selection([('draft', u'待提交'),
                                          ('submit', u'待审核'),
                                          ('done', u'已审核'),
                                          ], '进仓审批状态', default='draft')
    is_date_out_in = fields.Boolean('进仓日是否已确认', default=False)

    date_ship_state = fields.Selection([('draft', u'待提交'), ('submit', u'待审核'), ('done', u'已审核')], '出运船审批状态',
                                       default='draft')
    date_customer_finish_state = fields.Selection([('draft', u'待提交'), ('submit', u'待审核'), ('done', u'已审核')],
                                                  '客户交单日审批状态', default='draft')
    date_purchase_finish_state = fields.Selection([('draft', u'待提交'),
                                                   ('submit', u'待审核'),
                                                   ('done', u'已审核')], '供应商交单日审批状态', default='draft',
                                                  compute=compute_date_purchase_finish_state)

    date_purchase_finish_is_done = fields.Boolean('供应商交单是否完成', compute=compute_date_purchase_finish_is_done, store=True)

    date_delivered_id_done = fields.Boolean('工厂发货日期日否完成', compute=compute_date_delivered_id_done, store=True)

    date_all_state = fields.Selection([('10_date_approving', u'日期审批中'),
                                       ('20_no_date_out_in', u'出运日期待填'),
                                       ('23_no_date_delivered', u'工厂发货日期待填'),
                                       ('25_no_date_ship', u'船期待填'),
                                       ('27_no_date_finish', u'客户交单日期待填'),
                                       ('30_un_done', u'所有日期都已填未完成应收付款'),
                                       ('40_done', u'时间都已填未完成应收付款'),
                                       ('50_payable_done', u'应收付完成')
                                       ], '所有日期状态', default='20_no_date_out_in', store=True,
                                      compute=compute_date_all_state)
    hexiao_type = fields.Selection([('undefined', '...'), ('abnormal', u'异常核销'), ('write_off', u'正常核销')],
                                   default='undefined', string='核销类型')
    hexiao_date = fields.Date(u'核销时间')
    hexiao_uid = fields.Many2one('res.users', u'核销人')
    invoice_state = fields.Selection([('draft', u'未确认'), ('open', u'已确认'), ('paid', u'已付款')], string='账单状态',
                                     compute=compute_info)
    same_incoterm = fields.Boolean(u'价格条款是否一致', compute='compute_same')  # store=True,
    same_payment_term = fields.Boolean(u'付款条款是否一致', compute='compute_same')
    same_currency = fields.Boolean(u'币种是否一致', compute='compute_same')
    same_include_tax = fields.Boolean(u'含税是否一致', compute='compute_same')
    invoice_paid_state = fields.Selection([('a_paid', u'收付两清待核销'),
                                           ('b', u'已付清未收齐'),
                                           ('c', u'已收齐未付清'),
                                           ('d_no_paid', u'收付均未清'),
                                           ('e', '未确认')], '收款状态', store=True,
                                          compute=compute_invoice_paid_state)  # 应收应付分组情况
    # qq
    second_state = fields.Selection([('09', u'...'),
                                     ('10', u'正常待确认'),
                                     ('20', u'异常待确认'),
                                     ('30', u'收付均未清'),
                                     ('40', u'已收未付清'),
                                     ('50', '已付未收清'),
                                     ('60', u'正常待核销'),
                                     ('70', '应收付异常')], '二级状态', store=True, compute=compute_second_state)

    # outer_currency_id = fields.Many2one('res.currency', u'国外运保费货币', related='sol_id.outer_currency_id')
    # export_insurance_currency_id = fields.Many2one('res.currency', u'出口保险费货币',
    #                                                related='sol_id.export_insurance_currency_id')
    # other_currency_id = fields.Many2one('res.currency', u'其他国外费用货币', related='sol_id.other_currency_id')

    # is_tuopan = fields.Boolean(u'是否打托')

    tba_id = fields.Many2one('transport.bill.account', '转账调节单')
    incoterm_code = fields.Char('贸易术语', related='incoterm.code', readonly=True)
    org_sale_amount = fields.Monetary('销售金额', currency_field='sale_currency_id', compute=compute_info)

    org_sale_amount_new_discount = fields.Monetary(string='Discount', store=True, readonly=True, compute='amount_all',
                                                   track_visibility='always',)
    org_sale_amount_new_origin = fields.Monetary('原销售金额', currency_field='sale_currency_id',
                                                 compute=amount_all, store=True,track_visibility='onchange')  # 13ok
    org_real_sale_amount = fields.Monetary('实际销售金额', currency_field='sale_currency_id', compute=compute_info)  # ok
    org_sale_amount_new = fields.Monetary('销售金额', currency_field='sale_currency_id', compute=amount_all, track_visibility='onchange',
                                          store=True)  # 13ok 这个是对line_ids的出运统计

    org_hsname_actual_amount = fields.Monetary('实际出运金额', currency_field='sale_currency_id',
                                               compute=amount_all, store=True, track_visibility='onchange')  # 这个是对汇总后的实际出运金额的统计
    org_real_sale_amount_new = fields.Monetary('原始出运金额', currency_field='sale_currency_id',
                                               compute=amount_all, store=True, track_visibility='onchange')  # 这个是对汇总后的原始出运金额的统计if
    hsname_actual_amount_cny = fields.Monetary('实际人名币销售金额', currency_field='third_currency_id', compute=amount_all)
    real_sale_amount_cny = fields.Monetary('原始人名币销售金额', currency_field='third_currency_id', compute=amount_all)  # 13ok
    diff_real_sale_hsmame_actual_amount = fields.Monetary('出运账单和实际差额', currency_field='sale_currency_id',
                                                          compute=amount_all, store=True)  # 原始出运和实际出运的差额

    org_real_purchase_amount_new = fields.Monetary('原始采购金额', currency_field='third_currency_id', compute=amount_all,
                                                   store=True)  # 13ok
    purchase_hsname_actual_cost_total = fields.Monetary(u'实际采购金额', currency_field='third_currency_id',
                                                        compute=amount_all, store=True)  # 13ok先通过报关采购金额计算
    diff_real_purchase_hsname_actual_amount = fields.Monetary('采购账单和实际差额',
                                                              currency_field='third_currency_id',
                                                              compute=amount_all, store=True)  # 原始出运和实际出运的差额

    # 统计金额

    # 统计金额
    sale_amount = fields.Monetary('销售金额', currency_field='third_currency_id', compute=compute_info,
                                  )  # 13ok
    real_sale_amount = fields.Monetary('实际销售金额', currency_field='third_currency_id', compute=compute_info,
                                       )
    sale_commission_amount = fields.Monetary('经营计提金额', currency_field='third_currency_id', compute=compute_info)
    purchase_cost = fields.Monetary('采购成本', currency_field='third_currency_id', compute=compute_info,
                                    )
    fandian_amount = fields.Monetary('返点金额字', currency_field='third_currency_id', compute=compute_info,
                                     )
    stock_cost = fields.Monetary('库存成本', currency_field='third_currency_id', compute=compute_info,
                                 )  # 13ok
    other_cost = fields.Monetary('其他费用总计', currency_field='third_currency_id', compute=compute_info,
                                 )

    vat_diff_amount = fields.Monetary(u'增值税差额', currency_field='third_currency_id', compute=compute_info,
                                      )
    profit_amount = fields.Monetary('利润', currency_field='third_currency_id', compute=compute_info,
                                    )
    profit_ratio = fields.Float('利润率', digits=(2, 4), compute=compute_info)

    back_tax_amount = fields.Monetary('退税金额', currency_field='third_currency_id', compute=compute_info,
                                      )
    back_tax_amount_org = fields.Monetary('原始退税金额', currency_field='third_currency_id', compute=compute_info,
                                          )
    shoukuan_amount = fields.Monetary(u'收款金额', digits=(2, 4), compute=compute_info)
    fukuan_amount = fields.Monetary(u'付款金额', digits=(2, 4), compute=compute_info)

    sale_invoice_total = fields.Monetary(u'销售发票金额', compute=sale_invoice_amount)

    purhcase_invoice_total = fields.Monetary(u'采购发票金额', compute=purchase_invoice_amount)
    back_tax_invoice_total = fields.Monetary(u'退税发票金额', compute=back_tax_invoice_amount)

    sale_invoice_paid = fields.Monetary(u'销售发票已付', compute=sale_invoice_amount)
    purhcase_invoice_paid = fields.Monetary(u'采购发票已付', compute=purchase_invoice_amount)
    back_tax_invoice_paid = fields.Monetary(u'退税发票已付', compute=back_tax_invoice_amount)

    sale_invoice_balance = fields.Monetary(u'销售发票余额', compute=sale_invoice_amount)
    purhcase_invoice_balance = fields.Monetary(u'采购发票余额', compute=purchase_invoice_amount)
    back_tax_invoice_balance = fields.Monetary(u'退税发票余额', compute=back_tax_invoice_amount)

    account_type = fields.Selection([('tt', 'T/T'), ('lc', 'LC')], '收汇方式')
    credit_info = fields.Char('信用证信息')
    pack_line_ids2 = fields.One2many('transport.pack.line', related='pack_line_ids')
    # 不清楚什麽用
    date_out_in_related = fields.Date('进仓日期')
    date_in_related = fields.Date('入库日期')
    date_ship_related = fields.Date('出运船日期')
    date_customer_finish_related = fields.Date('客户交单日期')
    date_supplier_finish_related = fields.Date('供应商交单确认日期')
    # invoice_in_ids = fields.Many2many('account.invoice', u'发票汇总', compute=compute_info)
    mark_ids = fields.Many2many('transport.mark', 'ref_mark_tbill', 'tid', 'mid' '唛头')
    partner_mark_comb_ids = fields.Many2many('mark.comb', related='partner_id.mark_comb_ids')
    mark_comb_id = fields.Many2one('mark.comb', u'唛头组')
    partner_notice_id = fields.Many2one('res.partner', '通知人')
    forwarder_name = fields.Char('货代公司')
    settlement = fields.Char('结算方式')
    notice = fields.Text('注意事项')

    # akiny
    mark_html = fields.Html(u'唛头')

    # 金额计算
    ciq_amount = fields.Monetary('报关金额', compute=compute_ciq_amount, currency_field='sale_currency_id',
                                 digits=dp.get_precision('Money'), store=True)
    no_ciq_amount = fields.Monetary('不报关金额', compute=compute_ciq_amount, currency_field='company_currency_id',
                                    store=True)
    ciq_amount_new = fields.Monetary('报关金额', compute=compute_ciq_amount, currency_field='sale_currency_id', store=True,
                                     digits=dp.get_precision('Money'))
    amount_public1 = fields.Monetary('美元账户1', currency_field='sale_currency_id')
    amount_public2 = fields.Monetary('美元账户11', currency_field='sale_currency_id')
    amount_private1 = fields.Monetary('人民币账户15', currency_field='sale_currency_id')
    amount_private2 = fields.Monetary('人民币账户13', currency_field='sale_currency_id')
    amount_rmb3 = fields.Monetary('人民币3B', currency_field='sale_currency_id')
    amount_diff = fields.Monetary('差异处理', currency_field='sale_currency_id')
    amount_received = fields.Monetary('合计收款', currency_field='sale_currency_id')
    amount_real_payment = fields.Monetary('实际支付', currency_field='sale_currency_id')
    amount_account_payment = fields.Monetary('支付账户', currency_field='sale_currency_id')
    amount_account_adjust = fields.Monetary('账户调节', currency_field='sale_currency_id')
    all_purchase_invoice_fill = fields.Boolean('所有采购发票都已填写', compute=compute_invoice_amount)

    locked = fields.Boolean(u'锁定不允许修改')

    # 13已经添加   730：发货完成即开票完成：合规已审批更新为：出运日期待确认，invoiced更新为：出运日期已确认,交单日期审批完成后就发货并生成和确认发票。
    state = fields.Selection(Transport_Selection, '状态', default='draft', index=True, related='stage_id.state', store=True,
                             track_visibility='onchange')

    include_tax = fields.Boolean(u'含税')
    company_currency_id = fields.Many2one('res.currency', string='公司货币', related='company_id.currency_id',
                                          readonly=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True, string='公司货币')
    name = fields.Char('编号', default=lambda self: self.env['ir.sequence'].next_by_code('transport.bill'))
    ref = fields.Char(u'出运合同号')
    _sql_constraints = [
        ('ref_uniq', 'unique(ref)', u'存在重复的合同编号!')]
    date = fields.Date(u'出运日期')
    date_project = fields.Date(u'预计出运日期')
    payment_due_date = fields.Date('Payment Due Date')
    current_date_rate = fields.Float(u'当日汇率', group_operator=False)

    exchange_rate = fields.Float(u'目前汇率', compute=compute_exchange_rate)  # 13取消
    sale_currency_id = fields.Many2one('res.currency', u'交易货币', store=True)  # required=True,
    third_currency_id = fields.Many2one('res.currency', u'统计货币', required=True,
                                        default=lambda self: self.env.user.company_id.currency_id.id)

    partner_id = fields.Many2one('res.partner', '客户', domain=[('customer', '=', True)])  # required=True,
    partner_invoice_id = fields.Many2one('res.partner', string='发票地址', readonly=False)
    partner_shipping_id = fields.Many2one('res.partner', string='送货地址', required=False)
    user_id = fields.Many2one('res.users', u'业务员', default=lambda self: self.env.user.assistant_id.id)
    sale_assistant_id = fields.Many2one('res.users', u'业务助理', default=lambda self: self.env.user.id)
    company_id = fields.Many2one('res.company', '公司', required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    tuopan_weight = fields.Float(u'托盘重量')
    tuopan_volume = fields.Float(u'托盘体积')
    so_ids = fields.Many2many('sale.order', 'ref_tb_so', 'so_id', 'tb_id', string='销售订单', compute='compute_so_ids',
                              store=False)
    po_ids = fields.Many2many('purchase.order', string='采购订单', compute='compute_so_ids', store=False)

    @api.depends('line_ids')
    def compute_so_ids(self):
        for one in self:
            one.so_ids = one.line_ids.mapped('sol_id').mapped('order_id')
            one.po_ids = one.line_ids.mapped('lot_plan_ids').mapped('lot_id').mapped('po_id')

    cip_type = fields.Selection([('normal', u'正常报关'), ('buy', '第三方报关'), ('none', '不报关')], string=u'报关',
                                default='normal')
    line_ids = fields.One2many('transport.bill.line', 'bill_id', '明细', readonly=True,
                               states={'draft': [('readonly', False)]})  # 注意
    picking_ids = fields.Many2many('stock.picking', compute=compute_info, store=False,
                                   string='调拨')  # Tenyale 2.0的项目先保持M2M 不变
    stage1picking_ids = fields.Many2many('stock.picking', '', compute=compute_info, store=False,
                                         domain=[('picking_type_code', '=', 'incoming')],
                                         string='入库')  # Tenyale 2.0的项目先保持M2M 不变
    stage2picking_ids = fields.Many2many('stock.picking', compute=compute_info,
                                         domain=[('picking_type_code', '=', 'internal')],
                                         string='出库')  # Tenyale 2.0的项目先保持M2M 不变
    move_ids = fields.Many2many('stock.move', string='库存移动详情', compute=compute_info)
    stage1move_ids = fields.Many2many('stock.move', string='入库明细', compute=compute_info)
    stage2move_ids = fields.Many2many('stock.move', string='发货明细', compute=compute_info)
    stage1state = fields.Selection(Stage_Status, '入库', default=Stage_Status_Default, readonly=True)
    stage2state = fields.Selection(Stage_Status, '出库', default=Stage_Status_Default, readonly=True)
    sale_commission_ratio = fields.Float('经营计提', digits=(2, 4),
                                         default=lambda self: self.env['ir.config_parameter'].sudo().get_param(
                                             'addons_yjzy.sale_commission', '0.015'))
    incoterm = fields.Many2one('stock.incoterms', '贸易术语')
    qingguan_state = fields.Selection([('draft', u'未统计'), ('done', u'已统计')], string=u'清关统计', default='draft')
    qingguan_description_text = fields.Text(u'清关描述')
    qingguan_line_ids = fields.One2many('transport.qingguan.line', 'tb_id', '清关明细')
    description_baoguan = fields.Html('报关合同说明')
    date_out_in = fields.Date('进仓日期')
    date_in = fields.Date('入库日期')
    date_ship = fields.Date('出运船日期')
    date_customer_finish = fields.Date('客户交单日期')
    date_supplier_finish = fields.Date('供应商交单确认日期')
    sale_invoice_id = fields.Many2one('account.invoice', '销售发票')
    purchase_invoice_ids = fields.One2many('account.invoice', 'bill_id', '采购发票',
                                           domain=[('yjzy_type', '=', 'purchase')])
    purchase_invoice_ids_new = fields.One2many('account.invoice', 'bill_id', '采购发票_new',
                                               domain=[('invoice_attribute_all_in_one', '=', '120')])

    purchase_invoice_ids2 = fields.One2many('account.invoice', string='采购发票2',
                                            compute=compute_info)  # 顯示供應商的交單日期,这个以后再斟酌一下

    back_tax_invoice_id = fields.Many2one('account.invoice', '退税发票')

    all_invoice_ids = fields.One2many('account.invoice', 'bill_id', u'所有发票')
    all_sale_invoice_ids = fields.One2many('account.invoice', 'bill_id', u'所有销售发票', domain=[('yjzy_type', '=', 'sale')])
    all_purchase_invoice_ids = fields.One2many('account.invoice', 'bill_id', u'所有采购发票',
                                               domain=[('yjzy_type', '=', 'purchase')])
    all_back_tax_invoice_ids = fields.One2many('account.invoice', 'bill_id', u'所有退税发票',
                                               domain=[('yjzy_type', '=', 'back_tax')])
    all_back_tax_invoice_1_ids = fields.One2many('account.invoice', 'bill_id', u'所有退税发票',
                                                 domain=['|', ('yjzy_type', '=', 'back_tax'),
                                                         ('yjzy_type_1', '=', 'back_tax')])

    @api.depends('all_invoice_ids', 'all_invoice_ids.invoice_attribute_all_in_one', 'all_invoice_ids.amount_total',
                 'all_invoice_ids.residual')
    def compute_invoice_total_xf(self):
        for one in self:
            all_invoice_ids = one.all_invoice_ids
            fzzc_back_tax_invoice_ids = all_invoice_ids.filtered(
                lambda x: x.invoice_attribute_all_in_one in ['230', '330'])
            fz_back_tax_invoice_ids = all_invoice_ids.filtered(lambda x: x.invoice_attribute_all_in_one in ['330'])
            zc_back_tax_invoice_ids = all_invoice_ids.filtered(lambda x: x.invoice_attribute_all_in_one in ['230'])
            zc_purchase_invoice_ids = all_invoice_ids.filtered(
                lambda x: x.invoice_attribute_all_in_one in ['220'])  # 增加采购应付账单
            zc_sale_invoice_ids = all_invoice_ids.filtered(
                lambda x: x.invoice_attribute_all_in_one in ['210'])  # 增加采购应收账单
            fzzc_back_tax_invoice_total_new = sum(x.amount_total for x in fzzc_back_tax_invoice_ids)
            fz_back_tax_invoice_total_new = sum(x.amount_total for x in fz_back_tax_invoice_ids)
            zc_back_tax_invoice_total_new = sum(x.amount_total for x in zc_back_tax_invoice_ids)
            zc_purchase_invoice_total_new = sum(x.amount_total for x in zc_purchase_invoice_ids)
            zc_sale_invoice_total_new = sum(x.amount_total for x in zc_sale_invoice_ids)
            zc_invoice_profile_total_new = zc_purchase_invoice_total_new - zc_sale_invoice_total_new
            fzzc_back_tax_invoice_residual_total_new = sum(x.residual for x in fzzc_back_tax_invoice_ids)
            fz_back_tax_invoice_residual_total_new = sum(x.residual for x in fz_back_tax_invoice_ids)
            zc_back_tax_invoice_residual_total_new = sum(x.residual for x in zc_back_tax_invoice_ids)
            zc_purchase_invoice_residual_total_new = sum(x.residual for x in zc_purchase_invoice_ids)
            zc_sale_invoice_residual_total_new = sum(x.residual for x in zc_sale_invoice_ids)
            zc_invoice_profile_residual_total_new = zc_purchase_invoice_residual_total_new - zc_sale_invoice_residual_total_new
            one.fzzc_back_tax_invoice_total_new = fzzc_back_tax_invoice_total_new
            one.fz_back_tax_invoice_total_new = fz_back_tax_invoice_total_new
            one.zc_back_tax_invoice_total_new = zc_back_tax_invoice_total_new
            one.zc_invoice_profile_total_new = zc_invoice_profile_total_new
            one.zc_purchase_invoice_total_new = zc_purchase_invoice_total_new
            one.zc_sale_invoice_total_new = zc_sale_invoice_total_new
            one.fzzc_back_tax_invoice_residual_total_new = fzzc_back_tax_invoice_residual_total_new
            one.fz_back_tax_invoice_residual_total_new = fz_back_tax_invoice_residual_total_new
            one.zc_back_tax_invoice_residual_total_new = zc_back_tax_invoice_residual_total_new
            one.zc_invoice_profile_residual_total_new = zc_invoice_profile_residual_total_new
            one.zc_purchase_invoice_residual_total_new = zc_purchase_invoice_residual_total_new
            one.zc_sale_invoice_residual_total_new = zc_sale_invoice_residual_total_new

    fzzc_back_tax_invoice_total_new = fields.Monetary(u'费转增采退税合计原始金额', compute=compute_invoice_total_xf, store=True)
    fz_back_tax_invoice_total_new = fields.Monetary(u'费转退税原始金额', compute=compute_invoice_total_xf, store=True)
    zc_back_tax_invoice_total_new = fields.Monetary(u'增采退税原始金额', compute=compute_invoice_total_xf, store=True)
    zc_invoice_profile_total_new = fields.Monetary(u'增采净原始金额', compute=compute_invoice_total_xf, store=True)
    zc_purchase_invoice_total_new = fields.Monetary(u'增采应付原始金额', compute=compute_invoice_total_xf, store=True)
    zc_sale_invoice_total_new = fields.Monetary(u'增采应收原始金额', compute=compute_invoice_total_xf, store=True)

    fzzc_back_tax_invoice_residual_total_new = fields.Monetary(u'费转增采退税合计剩余金额', compute=compute_invoice_total_xf,
                                                               store=True)
    fz_back_tax_invoice_residual_total_new = fields.Monetary(u'费转退税剩余金额', compute=compute_invoice_total_xf, store=True)
    zc_back_tax_invoice_residual_total_new = fields.Monetary(u'增采退税剩余金额', compute=compute_invoice_total_xf, store=True)

    zc_invoice_profile_residual_total_new = fields.Monetary(u'增采净剩余金额', compute=compute_invoice_total_xf, store=True)
    zc_purchase_invoice_residual_total_new = fields.Monetary(u'增采应付剩余金额', compute=compute_invoice_total_xf, store=True)
    zc_sale_invoice_residual_total_new = fields.Monetary(u'增采应收剩余金额', compute=compute_invoice_total_xf, store=True)
    tb_vendor_ids = fields.One2many('transport.bill.vendor', 'tb_id', u'供应商发运单')

    sale_invoice_count = fields.Integer(u'销售发票数', compute='compute_invoice_count')
    purchase_invoice_count = fields.Integer(u'采购发票数', compute='compute_invoice_count')
    back_tax_invoice_count = fields.Integer(u'退税发票数', compute='compute_invoice_count')
    fhtzd_count = fields.Integer(u'发货通知单数量', compute='compute_invoice_count')
    qg_count = fields.Integer(u'清关数量', compute='compute_invoice_count')
    bg_count = fields.Integer(u'报关数量', compute='compute_invoice_count')

    @api.depends('purchase_invoice_ids', 'sale_invoice_id', 'back_tax_invoice_id', 'tb_vendor_ids',
                 'qingguan_line_ids', 'hsname_ids')
    def compute_invoice_count(self):
        for one in self:
            one.purchase_invoice_count = len(one.purchase_invoice_ids.filtered(lambda x: x.yjzy_type == 'purchase'))
            one.sale_invoice_count = one.sale_invoice_id and 1 or 0
            one.back_tax_invoice_count = one.back_tax_invoice_id and 1 or 0
            one.fhtzd_count = len(one.tb_vendor_ids)
            one.qg_count = one.qingguan_line_ids and 1 or 0
            one.bg_count = one.hsname_ids and 1 or 0

    tbl_lot_ids = fields.One2many('bill.line.lot', 'tb_id', u'批次明细')
    gongsi_id = fields.Many2one('gongsi', '销售主体')
    purchase_gongsi_id = fields.Many2one('gongsi', '采购主体')
    pallet_type = fields.Selection([('ctns', 'CTNS'), ('plts', 'PLTS'), ('PKGS', 'PKGS')], u'包装类型')
    pallet_qty = fields.Integer(u'托盘数')
    is_editable = fields.Boolean(u'可编辑')
    contract_type = fields.Selection([('a', '模式1'), ('b', '模式2'), ('c', '模式3')], '合同类型', default='c')
    # 其他费用 fee_inner,fee_rmb1,fee_rmb2,fee_outer,fee_export_insurance,fee_other
    fee_inner = fields.Monetary('国内运杂费', currency_field='company_currency_id')
    fee_rmb1 = fields.Monetary('人民币费用1', currency_field='company_currency_id')
    fee_rmb1_note = fields.Text('人名币费用1备注')
    fee_rmb2 = fields.Monetary('人民币费用2', currency_field='company_currency_id')
    fee_rmb2_note = fields.Text('人名币费用2备注')

    outer_currency_id = fields.Many2one('res.currency', '国外运保费货币', required=True)
    fee_outer = fields.Monetary('国外运保费', currency_field='outer_currency_id')
    fee_outer_need = fields.Boolean(u'国外运保费计入应收', default=False)

    fee_export_insurance = fields.Monetary('出口保险费', currency_field='export_insurance_currency_id')
    export_insurance_currency_id = fields.Many2one('res.currency', '出口保险费货币')
    fee_other = fields.Monetary('其他外币费用', currency_field='other_currency_id')
    fee_other_note = fields.Text('其他外币费用备注')

    other_currency_id = fields.Many2one('res.currency', '其他外币费用货币')

    fee_inner_so = fields.Monetary(u'国内运杂费', currency_field='company_currency_id', compute=_get_fee_inner_so)
    fee_rmb1_so = fields.Monetary(u'人民币费用1', currency_field='company_currency_id', compute=_get_fee_rmb1_so)
    fee_rmb2_so = fields.Monetary(u'人民币费用2', currency_field='company_currency_id', compute=_get_fee_rmb2_so)
    fee_outer_so = fields.Monetary(u'国外运保费', currency_field='other_currency_id', compute=_get_fee_outer_so)
    fee_export_insurance_so = fields.Monetary(u'出口保险费', currency_field='other_currency_id',
                                              compute=_get_fee_export_insurance_so)
    fee_other_so = fields.Monetary(u'其他外币费用', currency_field='other_currency_id', compute=_get_fee_other_so)
    is_fee_done = fields.Boolean(u'默认费用完成')
    sale_type = fields.Selection([('inner', '自营'), ('proxy', '代理')], u'业务类型', default='inner')
    hs_fill = fields.Selection(
        [('all', u'全部'), ('sale_purchase', u'销售采购'), ('packaging', u'包装资料'), ('others', u'其他信息')], '报关显示',
        default='sale_purchase')

    hs_fill_sale_purchase = fields.Boolean('报关invoice信息')
    hs_fill_sale_packaging = fields.Boolean('报关packing信息')
    hs_fill_sale_others = fields.Boolean('报关其他信息')
    gold_sample_state = fields.Selection([('all', '全部有'), ('part', '部分有'), ('none', '无金样')], '样金管理',
                                         compute=compute_info)
    ps_state = fields.Selection([('all', '全部有'), ('part', '部分有'), ('none', '无PS')], 'PS管理',
                                compute=compute_info)
    description = fields.Text(u'出运备注')
    mark_text = fields.Text(u'唛头')
    wharf_src_id = fields.Many2one('stock.wharf', '装船港')
    wharf_dest_id = fields.Many2one('stock.wharf', '目的港')
    partner_country_id = fields.Many2one('res.country', '贸易国别')
    invoice_title = fields.Char('发票抬头')
    notice_man = fields.Text(u'通知人')
    delivery_man = fields.Text(u'发货人')
    demand_info = fields.Text(u'交单要求')
    payment_term_id = fields.Many2one('account.payment.term', string='付款条款')
    operation_wizard = fields.Selection([('first', u'选择客户'),
                                         ('second', u'添加出运明细'),
                                         ('third', u'填写出运数量'),
                                         ('fourth', u'生成出运合同号'),
                                         ('fifth', u'填写剩余字段')], '操作向导', default='first')
    # -----

    production_sale_unit = fields.Char('生产销售单位')
    # 出运成本单据

    budget_amount = fields.Monetary('预算', compute=compute_info, currency_field='company_currency_id')
    budget_reset_amount = fields.Monetary('预算剩余', compute=compute_info, currency_field='company_currency_id')
    budget_ids = fields.One2many('budget.budget', 'tb_id', u'预算明细')
    expense_ids = fields.One2many('hr.expense', 'tb_id', u'费用')

    trans_type = fields.Selection([('sea', 'By SEA'), ('air', 'By AIR'), ('express', 'By Express'), ('other', u'其他')],
                                  '运输方式')
    insurance_info = fields.Char('保险说明')

    pack_line_ids = fields.One2many('transport.pack.line', 'bill_id', '装箱统计')

    qingguan_description = fields.Html(u'清关描述')  # 13取消

    # akiny 新增
    qingguan_amount = fields.Monetary(u'清关总金额', currency_field='sale_currency_id', compute=_get_qingguan)
    qingguan_qty_total = fields.Float(u'清关总数量', compute=_get_qingguan)
    qingguan_case_qty_total = fields.Float(u'清关总箱数', compute=_get_qingguan)
    qingguan_net_weight_total = fields.Float(u'清关总净重', compute=_get_qingguan)
    qingguan_gross_wtight_total = fields.Float(u'清关总毛重', compute=_get_qingguan)
    qingguan_volume_total = fields.Float(u'清关总体积', compute=_get_qingguan)




    # 单证信息

    is_done_plan = fields.Boolean(u'默认调拨计划完成')
    is_done_tuopan = fields.Boolean(u'托盘分配完成')
    is_done_tb_vendor = fields.Boolean(u'供应商发运完成')
    is_done_all_document = fields.Boolean(u'所有自动计算完成')

    # 审批记录 akiny
    submit_date = fields.Date('提交审批时间')
    submit_uid = fields.Many2one('res.users', u'提交审批')
    sales_confirm_date = fields.Date('责任人审批时间')
    sales_confirm_uid = fields.Many2one('res.users', u'责任人审批')
    approve_date = fields.Date('审批完成日期')
    approve_uid = fields.Many2one('res.users', u'合规审批')
    confirmed_date = fields.Date('单证审批日期')
    confirmed_uid = fields.Many2one('res.users', '单证审批')
    delivered_date = fields.Datetime('出运完成日期')
    delivered_uid = fields.Many2one('res.users', u'出运完成')
    invoiced_date = fields.Date('开票日期')
    invoiced_uid = fields.Many2one('res.users', u'开票完成')
    paid_date = fields.Date('收款日期')
    paid_uid = fields.Many2one('res.users', u'收款完成')

    return_picking_ids = fields.Many2many('stock.picking', 'ref_tb_return_picking', 'pid', 'tid', '退货单')
    return4return_picking_ids = fields.Many2many('stock.picking', 'ref_tb_return4return_picking', 'pid', 'tid', '重发')

    # def add_customer(self):
    #     self.ensure_one()
    #     form_view = self.env.ref('yjzy_extend.view_transport_bill_wkf_form').id
    #     # tree_view = self.env.ref('yjzy_extend.new_order_transport_same_tree')
    #     ctx = self.env.context
    #     # if ctx.get('default_open', '') == 'partner':
    #         # return {'type': 'ir.actions.act_window_close'}
    #
    #     return {
    #         'name': _(u'添加客户'),
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'transport.bill',
    #         'views': [(form_view, 'form')],
    #         'res_id': self.id,
    #         'target': 'new',
    #         }

    # if ctx.get('default_open', '') == 'sol':
    #     return self.open_wizard_transport4sol()

    @api.onchange('ref')
    def onchange_ref(self):
        ref = self.ref
        if ref != False:
            ref = self.ref.strip()
        self.ref = ref

    def action_hexiao(self):
        today = fields.datetime.now()
        stage_id = self._stage_find(domain=[('code', '=', '008')])
        stage_preview = self.stage_id
        user = self.env.user
        second_state = self.second_state
        hexiao_type = 'undefined'
        # group = self.env.user.groups_id
        if user not in stage_preview.user_ids:
            raise Warning('您没有权限核销')
        else:
            if second_state == '60':
                hexiao_type = 'write_off'
            elif second_state == 70:
                hexiao_type = 'abnormal'
            self.write({'hexiao_uid': self.env.user.id,
                        'hexiao_date': today,
                        # 'state':'sales_approve',
                        'stage_id': stage_id.id,
                        'hexiao_type': hexiao_type})

    def compute_stage_id(self):
        if self.state == 'draft':
            self.stage_id = self.env.ref('yjzy_extend.stage_tb_draft').id
        if self.state == 'submit':
            self.stage_id = self.env.ref('yjzy_extend.stage_tb_submit').id
        if self.state == 'sales_approve':
            self.stage_id = self.env.ref('yjzy_extend.stage_tb_sales_approve').id
        if self.state == 'approve':
            self.stage_id = self.env.ref('yjzy_extend.stage_tb_approve').id
        if self.state == 'invoiced':
            self.stage_id = self.env.ref('yjzy_extend.stage_tb_invoiced').id
        if self.state == 'abnormal':
            self.stage_id = self.env.ref('yjzy_extend.stage_tb_abnormal').id
        if self.state == 'verifying':
            self.stage_id = self.env.ref('yjzy_extend.stage_tb_verifying').id
        if self.state == 'done':
            self.stage_id = self.env.ref('yjzy_extend.stage_tb_done').id
        if self.state == 'cancel':
            self.stage_id = self.env.ref('yjzy_extend.stage_tb_cancel').id
        if self.state == 'refused':
            self.stage_id = self.env.ref('yjzy_extend.stage_tb_refused').id

    # akiny 向导
    def edit_line_ids(self):
        self.ensure_one()
        form_view = self.env.ref('yjzy_extend.view_transport_bill_wkf_edit_line_form').id
        return {
            'name': _(u'添加客户'),
            'view_type': 'form',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'transport.bill',
            'views': [(form_view, 'form')],
            'res_id': self.id,
            'target': 'new',
        }

    def open_ref_document(self):
        self.ensure_one()
        self.make_all_document()
        form_view = self.env.ref('yjzy_extend.view_transport_bill_wkf_document_form').id
        return {
            'name': _(u'添加客户'),
            'view_type': 'form',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'transport.bill',
            'views': [(form_view, 'form')],
            'res_id': self.id,
            'target': 'new',
        }

    # 退回发货
    def make_picking_return(self):

        wizard_obj = self.env['stock.return.picking']

        pickings = self.stage2picking_ids | self.stage1picking_ids

        return_picking_ids = []
        for pk in pickings:
            ctx = {'active_ids': [pk.id], 'active_id': pk.id}
            wizard = wizard_obj.with_context(ctx).create({
            })
            for wzline in wizard.product_return_moves:
                wzline.to_refund = True
                wzline.quantity = wzline.move_id.quantity_done
            action = wizard.create_returns()
            return_picking_ids.append(action['res_id'])
            print('=make_picking_return==', wizard, action)
        self.write({'return4return_picking_ids': [(4, pid) for pid in return_picking_ids]})  # 参考

    def make_return4return(self):
        wizard_obj = self.env['stock.return.picking']

        return4return_picking_ids = []
        for pk in self.return_picking_ids:
            ctx = {'active_ids': [pk.id], 'active_id': pk.id}
            wizard = wizard_obj.with_context(ctx).create({
            })
            for wzline in wizard.product_return_moves:
                wzline.to_refund = True
                wzline.quantity = wzline.move_id.quantity_done
            action = wizard.create_returns()
            return4return_picking_ids.append(action['res_id'])
            print('=make_return4return==', wizard, action)
        self.write({'return_picking_ids': [(4, pid) for pid in return4return_picking_ids]})

    # 当手动创建发票的时候，用这个来关联出运单
    def compute_sale_invoice_id(self):
        sale_invoice_id = self.all_invoice_ids.filtered(lambda x: x.yjzy_type == 'sale')
        self.sale_invoice_id = sale_invoice_id[0]

    @api.multi
    def _get_printed_report_name(self):
        self.ensure_one()
        # date = fields.datetime.now().strftime('%m%d')
        return _('%s-Commercial Invoice') % (self.ref)

    @api.multi
    def _get_printed_report_name_packing_qingguan(self):
        self.ensure_one()
        # date = fields.datetime.now().strftime('%m%d')
        return _('%s-Packing List') % (self.ref)

    # akiny 计算出运合同号 13ok
    def compute_tb_ref(self):
        so_ids_len = len(self.so_ids)
        ref = ''
        ref2 = ''
        for index, x in enumerate(self.so_ids):
            print('-index-', index, so_ids_len, x.rest_tb_qty_total)
            if index + 1 != so_ids_len:
                if x.rest_tb_qty_total == 0 and x.tb_count == 1:
                    ref += '%s/' % (x.contract_code)
                else:
                    ref += '%s-%s/' % (x.contract_code, x.tb_count)
            else:
                if x.rest_tb_qty_total == 0 and x.tb_count == 1:
                    ref2 = '%s%s' % (ref, x.contract_code)
                else:
                    ref2 = '%s%s-%s' % (ref, x.contract_code, x.tb_count)
        self.ref = ref2

    def compute_fee(self):
        if not self.is_fee_done:
            self.fee_inner = self.fee_inner_so
            self.fee_rmb1 = self.fee_rmb1_so
            self.fee_rmb2 = self.fee_rmb2_so
            self.fee_outer = self.fee_outer_so
            self.fee_export_insurance = self.fee_export_insurance_so
            self.fee_other = self.fee_other_so
            self.is_fee_done = True

    def open_fee(self):
        if self.is_fee_done == True:
            war = ''
            war += '国内运杂费： %s\n' % self.fee_inner_so
            war += '人名币费用1： %s\n' % self.fee_rmb1_so
            war += '人名币费用2： %s\n' % self.fee_rmb2_so
            war += '国外运保费： %s\n' % self.fee_outer_so
            war += '出口保险费： %s\n' % self.fee_export_insurance_so
            war += '其他外币费用： %s\n' % self.fee_other_so
            raise Warning(war)

    # akiny 如果有不同的就添加编辑，可以打开查看
    def open_same(self):
        self.ensure_one()
        # form_view = self.env.ref('yjzy_extend.view_account_supplier_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.new_order_transport_same_tree')
        ctx = self.env.context
        if ctx.get('default_open', '') == 'incoterm':
            self.ensure_one()
            return {
                'name': u'价格条款对比',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'views': [(tree_view.id, 'tree')],
                'domain': [('id', 'in', [x.id for x in self.so_ids])],
                'context': {'same_incoterm': 1},
            }
        if ctx.get('default_open', '') == 'payment_term':
            self.ensure_one()
            return {
                'name': u'价格条款对比',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'views': [(tree_view.id, 'tree')],
                'domain': [('id', 'in', [x.id for x in self.so_ids])],
                'context': {'same_payment_term': 1},
            }
        if ctx.get('default_open', '') == 'currency':
            self.ensure_one()
            return {
                'name': u'价格条款对比',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'views': [(tree_view.id, 'tree')],
                'domain': [('id', 'in', [x.id for x in self.so_ids])],
                'context': {'same_currency': 1},
            }
        if ctx.get('default_open', '') == 'include_tax':
            self.ensure_one()
            return {
                'name': u'价格条款对比',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'sale.order',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'views': [(tree_view.id, 'tree')],
                'domain': [('id', 'in', [x.id for x in self.so_ids])],
                'context': {'same_include_tax': 1},
            }

    # ctx = self.env.context
    # res = super(account_payment, self).default_get(fields)
    #
    # print('==========dg======', ctx)
    #
    # if ctx.get('default_sfk_type', '') == 'jiehui':
    #     res.update({
    #         'partner_id': self.env['res.partner'].search([('name', '=', '未定义')], limit=1).id
    #     })
    # 同时计算出运资料和生成出运合同号
    def make_all_document(self):
        self.make_sale_purchase_collect()
        self.create_qingguan_lines()
        self.make_tb_vendor()
        # self.split_tuopan_weight()
        # self.split_tuopan_weight2vendor()
        self.compute_tb_ref()
        self.compute_fee()
        self.operation_wizard = 'fifth'
        self.is_done_all_document = True

    def split_tuopan_all(self):
        self.split_tuopan_weight()
        self.split_tuopan_weight2vendor()

    def make_sale_purchase_collect(self):
        self.make_sale_collect()
        self.make_purchase_collect()
        # self.split_tuopan_weight_baoguan()

    def unlink_bgzl(self):
        self.hsname_ids.unlink()
        self.comb_ids.unlink()
        self.btls_hs_ids.unlink()
        self.btls_comb_ids.unlink()
        self.btl_supplier_ids.unlink()
        self.qingguan_line_ids.unlink()
        self.tb_vendor_ids.unlink()

    @api.multi
    def action_save_test(self):
        # your code
        self.ensure_one()
        # close popup
        return {'type': 'ir.actions.act_window_close'}

    def action_customer_date_state_submit(self):
        date_type = self.env.context.get('date_type')
        for one in self:
            if date_type == 'date_out_in':
                if not one.date_out_in:
                    raise Warning('请先填写进仓日期')
                if not one.date_out_in_att:
                    raise Warning('请提交进仓日期附件')
                one.date_out_in_state = 'submit'

            if date_type == 'date_ship':
                if not one.date_ship:
                    raise Warning('请先填写出运船日期')
                if not one.date_ship_att:
                    raise Warning('请提交出运船日期附件')
                one.date_ship_state = 'done'  # 由原来的两步审批，直接提交完成

            if date_type == 'date_customer_finish':
                if not one.date_customer_finish:
                    raise Warning('请先填写客户交单日期')
                if not one.date_customer_finish_att:
                    raise Warning('请提交客户交单日期附件')
                one.date_customer_finish_state = 'done'

    # 日期审批完成后直接出运并生成账单同时更新进仓日期到对应的发票 qq
    def action_customer_date_state_done(self):
        date_type = self.env.context.get('date_type')
        print('date_type_akiny', date_type)
        for one in self:
            # if self.env.ref('akiny.group_trans_hegui') not in self.env.user.groups_id:
            #     raise Warning('您没有审批的权限！')
            if date_type == 'date_out_in':
                one.date_out_in_state = 'done'
                if one.state not in ['delivered', 'invoiced']:
                    # one.state = 'invoiced'
                    one.stage_id = self._stage_find(domain=[('code', '=', '005')])
                    # one.onece_all_stage()
                    # one.make_all_invoice()
                    one.action_invoiced()
                    one.sync_data2invoice()
                    one.is_date_out_in = True
            if date_type == 'date_ship':
                one.date_ship_state = 'done'
            if date_type == 'date_customer_finish':
                one.date_customer_finish_state = 'done'

    def action_customer_date_state_refuse(self):
        date_type = self.env.context.get('date_type')
        for one in self:
            if date_type == 'date_out_in':
                one.date_out_in_state = 'refuse'
            if date_type == 'date_ship':
                one.date_ship_state = 'refuse'
            if date_type == 'date_customer_finish':
                one.date_customer_finish_state = 'refuse'

    @api.onchange('contract_type')
    def onchange_contract_type(self):
        gongsi_obj = self.env['gongsi']
        if self.contract_type == 'b':
            self.gongsi_id = gongsi_obj.search([('name', '=', 'BERTZ')], limit=1)
            self.purchase_gongsi_id = gongsi_obj.search([('name', '=', '天宇进出口')], limit=1)

    @api.onchange('date_out_in')
    def onchange_date_out_in(self):
        self.date_out_in_related = self.date_out_in

    @api.onchange('date_in')
    def onchange_date_in(self):
        self.date_in_related = self.date_in

    @api.onchange('date_ship')
    def onchange_date_ship(self):
        self.date_ship_related = self.date_ship

    @api.onchange('date_customer_finish')
    def onchange_date_customer_finish(self):
        self.date_customer_finish_related = self.date_customer_finish

    @api.onchange('date_supplier_finish')
    def onchange_date_supplier_finish(self):
        self.date_supplier_finish_related = self.date_supplier_finish

    # @api.constrains('line_ids')
    # def check_lines(self):
    #     for one in self:
    #         if len(one.line_ids) != len(one.line_ids.mapped('sol_id')):
    #             raise Warning('不能创建相同 销售明细 的出运明细行')
    # 13ok 状态更行  org   org1  amount_total   tb_approve_po_amount_total   so_line_akiny today  other_price_akiny  hegui
    @api.model
    def create(self, vals):
        one = super(transport_bill, self).create(vals)
        budget = self.env['budget.budget'].create({
            'type': 'transport',
            'tb_id': one.id,
        })
        return one

    # # 13ok
    # @api.constrains('ref')
    # def check_contract_code(self):
    #     for one in self:
    #         if one.ref and self.search_count([('ref', '=', one.ref)]) > 1:
    #             raise Warning('出运合同号重复')
    #

    @api.multi
    # def copy(self, default=None):
    #     self.ensure_one()
    #     default = dict(default or {})
    #     if 'ref' not in default:
    #         default['ref'] = "%s(copy)" % self.contract_code
    #     return super(transport_bill, self).copy(default)
    def action_sale_purchase(self):
        for one in self:
            one.hs_fill = 'sale_purchase'

    def action_packaging(self):
        for one in self:
            one.hs_fill = 'packaging'

    def action_others(self):
        for one in self:
            one.hs_fill = 'others'

    def unlink(self):
        for one in self:
            sale_orders = one.mapped('so_ids')
            if one.state != 'cancel':
                raise Warning(u'只有取消状态允许删除！')
            else:
                if len(one.line_ids) != 0:
                    raise Warning(u'请先删除明细行！')
                else:
                    one.budget_ids.unlink()
                    sale_lines = sale_orders.mapped('order_line')
                    one.line_ids.unlink()
                    sale_lines.compute_rest_tb_qty()
                    print('budget', one.budget_ids, sale_lines)
        return super(transport_bill, self).unlink()

    def unlink_budegt_ids(self):
        self.budget_ids.unlink()

    # 13ok
    @api.multi
    def name_get(self):
        ctx = self.env.context
        result = []
        only_ref = self.env.context.get('only_ref')
        min_add = self.env.context.get('min_add')

        # fhtzd = self.env.context.get(fhtzd)
        for one in self:
            purchase_amount_min_add_rest_total = round(one.purchase_amount_min_add_rest_total, 2)
            print('---name_get---', one)
            name = ''
            if one.ref:
                if only_ref:
                    name = one.ref
                elif min_add:
                    name = '%s:%s' % (one.ref, purchase_amount_min_add_rest_total)
                else:
                    name += ' %s' % one.ref
            result.append((one.id, name))
            print('---name_get---', result)

        return result

    # 13ok
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('ref', '=ilike', name + '%'), ('name', operator, name)]
        records = self.search(domain + args, limit=limit)
        return records.name_get()

    @api.onchange('incoterm')
    def onchange_incoterm(self):
        self.fee_outer_need = False
        # if self.incoterm.code == 'CIF':
        #     self.fee_outer_need = True
        # else:
        #     self.fee_outer_need = False

    # 13ok
    def split_tuopan_weight(self):
        # if self.pallet_type == 'plts':
        #     # if self.tuopan_weight <= 0 or self.tuopan_volume <=0:
        #     #     raise Warning(u'请先设置托盘重量和体积')

        qinguan_count = sum([x.qty for x in self.qingguan_line_ids])
        if qinguan_count > 0:
            for line in self.qingguan_line_ids:
                line.tuopan_weight = line.qty / qinguan_count * self.tuopan_weight

        hsl_count = sum([x.qty_max for x in self.hsname_ids])
        if hsl_count > 0:
            for line in self.hsname_ids:
                line.tuopan_weight = line.qty_max / hsl_count * self.tuopan_weight

        # ================tuopan_volume
        qinguan_volume = sum([x.volume for x in self.qingguan_line_ids])
        if qinguan_volume > 0:
            for line in self.qingguan_line_ids:
                line.tuopan_volume = line.volume / qinguan_volume * self.tuopan_volume

        hsl_volume = sum([x.volume for x in self.hsname_ids])
        if hsl_volume > 0:
            for line in self.hsname_ids:
                line.tuopan_volume = line.volume / hsl_volume * self.tuopan_volume

        self.is_done_tuopan = True

    # 13不需要
    def split_tuopan_weight_qingguan(self):
        # if self.pallet_type == 'plts':
        # if self.tuopan_weight <= 0 or self.tuopan_volume <= 0:
        #     raise Warning(u'请先设置托盘重量和体积')

        qinguan_count = sum([x.qty for x in self.qingguan_line_ids])
        if qinguan_count > 0:
            for line in self.qingguan_line_ids:
                line.tuopan_weight = line.qty / qinguan_count * self.tuopan_weight
        qinguan_volume = sum([x.volume for x in self.qingguan_line_ids])
        if qinguan_volume > 0:
            for line in self.qingguan_line_ids:
                line.tuopan_volume = line.volume / qinguan_volume * self.tuopan_volume

    def split_tuopan_weight_baoguan(self):
        # if self.pallet_type == 'plts':
        # if self.tuopan_weight <= 0 or self.tuopan_volume <=0:
        #     raise Warning(u'请先设置托盘重量和体积')
        hsl_count = sum([x.qty_max for x in self.hsname_ids])
        if hsl_count > 0:
            for line in self.hsname_ids:
                line.tuopan_weight = line.qty_max / hsl_count * self.tuopan_weight
        hsl_volume = sum([x.volume for x in self.hsname_ids])
        if hsl_volume > 0:
            for line in self.hsname_ids:
                line.tuopan_volume = line.volume / hsl_volume * self.tuopan_volume

    def split_tuopan_weight2vendor(self):
        # if self.pallet_type == 'plts':
        vendor_lines = self.tb_vendor_ids.mapped('line_ids')

        # print('===split_tuopan_weight2vendor==0:', self.tb_vendor_ids, vendor_lines)

        # if self.tuopan_weight <= 0 or self.tuopan_volume <=0:
        #     raise Warning(u'请先设置托盘重量和体积')

        all_count = sum([x.qty for x in vendor_lines])
        print('===split_tuopan_weight2vendor==1:', all_count)
        if all_count > 0:
            for line in vendor_lines:
                line.tuopan_weight = line.qty / all_count * self.tuopan_weight

        all_volume = sum([x.volume for x in vendor_lines])
        print('===split_tuopan_weight2vendor==2:', all_volume)
        if all_volume > 0:
            for line in vendor_lines:
                line.tuopan_volume = line.volume / all_volume * self.tuopan_volume

    # 13ok
    def update_back_tax(self):
        for line in self.line_ids:
            line.back_tax = line.product_id.back_tax
        self.btls_hs_ids.compute_price2()
        self.compute_info()

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'draft':
            return 'yjzy_extend.mt_tb_draft'
        elif 'state' in init_values and self.state == 'w_sale_manager':
            return 'yjzy_extend.mt_tb_w_sale_manager'
        elif 'state' in init_values and self.state == 'w_sale_director':
            return 'yjzy_extend.mt_tb_w_sale_director'
        elif 'state' in init_values and self.state == 'confirmed':
            return 'yjzy_extend.mt_tb_confirmed'


        elif 'state' in init_values and self.state == 'done':
            return 'yjzy_extend.mt_tb_done'

        return super(transport_bill, self)._track_subtype(init_values)

    @api.onchange('partner_id')
    def onchange_partner(self):
        mans = self.partner_id.child_ids
        ship_man = mans.filtered(lambda x: x.type == 'delivery')
        notice_man = mans.filtered(lambda x: x.type == 'notice')
        addr = self.partner_id.address_get(['delivery', 'invoice'])

        values = {
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }

        self.partner_invoice_id = addr['invoice']
        self.partner_shipping_id = addr['delivery']
        self.invoice_title = self.partner_shipping_id.invoice_title
        # self.mark_ids = self.partner_shipping_id.mark_ids
        self.mark_text = self.partner_shipping_id.mark_text
        self.notice_man = self.partner_shipping_id.notice_man
        self.wharf_src_id = self.partner_shipping_id.wharf_src_id
        self.wharf_dest_id = self.partner_shipping_id.wharf_dest_id
        # self.payment_term_id = self.partner_id.property_payment_term_id
        self.partner_country_id = self.partner_shipping_id.country_id
        self.qingguan_name = self.partner_id.full_name
        self.qingguan_address = self.partner_id.address_text
        self.qingguan_phone = self.partner_id.phone

        # akiny
        # self.user_id = self.partner_id.user_id
        # self.sale_currency_id = self.partner_id.property_product_pricelist.currency_id

        #   self.mark_html = self.partner_shipping_id.mark_html.currency_id
        # akiny
        ##self.outer_currency_id = self.sale_currency_id
        # self.notice_man = self.partner_id.notice_man
        self.delivery_man = self.partner_shipping_id.delivery_man
        self.demand_info = self.partner_shipping_id.demand_info
        self.contract_type = self.partner_id.contract_type
        self.gongsi_id = self.partner_id.gongsi_id
        self.purchase_gongsi_id = self.partner_id.purchase_gongsi_id
        if self.operation_wizard != 'fifth':
            self.operation_wizard = 'second'

    @api.onchange('partner_shipping_id')
    def onchange_partner_shipping(self):
        self.invoice_title = self.partner_shipping_id.invoice_title
        # self.mark_ids = self.partner_shipping_id.mark_ids
        self.mark_text = self.partner_shipping_id.mark_text
        self.notice_man = self.partner_shipping_id.notice_man
        self.wharf_src_id = self.partner_shipping_id.wharf_src_id
        self.wharf_dest_id = self.partner_shipping_id.wharf_dest_id
        # self.payment_term_id = self.partner_id.property_payment_term_id
        self.partner_country_id = self.partner_shipping_id.country_id
        self.delivery_man = self.partner_shipping_id.delivery_man
        self.demand_info = self.partner_shipping_id.demand_info
        self.contract_type = self.partner_id.contract_type
        self.gongsi_id = self.partner_id.gongsi_id
        self.purchase_gongsi_id = self.partner_id.purchase_gongsi_id

    def finish_delivery_qty(self):
        self.amount_all()
        if self.operation_wizard != 'fifth':
            self.operation_wizard = 'fourth'
        self._sale_purchase_amount()

    def make_tb_vendor(self):
        # print('>>>>make_tb_vendor')
        self.ensure_one()
        tbv_obj = self.env['transport.bill.vendor']
        self.tb_vendor_ids.unlink()
        plans = self.line_ids.mapped('lot_plan_ids').filtered(lambda x: x.stage_1)
        suppliers = plans.mapped('lot_id').mapped('supplier_id')
        for supplier in suppliers:
            tbv = tbv_obj.create({
                'partner_id': supplier.id,
                'tb_id': self.id,
            })
            tbv.make_lines()
        self.is_done_tb_vendor = True
        self.split_tuopan_weight2vendor()

    # 13取消
    def make_tbl_lot(self):
        for one in self:
            one.tbl_lot_ids = None
            # 创建明细批次
            one.line_ids.compute_tbl_lot()
            # 创建供应商发货单
            one.make_tb_vendor()

    @api.model
    def get_account_by_config_parameter(self):
        param_obj = self.env['ir.config_parameter'].sudo()
        account_obj = self.env['account.account']

        def _get_account_id8param(param):
            account_code = param_obj.get_param(param)
            account = account_obj.search([('code', '=', account_code)], limit=1)
            if not account:
                raise Warning('没有找到 %s 对应的科目,请联系管理员' % param)
            return account

        param_list = [
            'addons_yjzy.amount_public1',
            'addons_yjzy.amount_public2',
            'addons_yjzy.amount_private1',
            'addons_yjzy.amount_private2',
            'addons_yjzy.amount_rmb3',
            'addons_yjzy.amount_diff',
        ]
        res = [_get_account_id8param(i) for i in param_list]
        # print(('===========', res))
        return res

    def get_payment_info(self):
        param_obj = self.env['ir.config_parameter']
        account_public1, account_public2, account_private1, account_private2, account_rmb3, account_diff = self.get_account_by_config_parameter()

        def get_move_amount(m, to_currency):
            if m.amount_currency:
                return m.currency_id.compute(move.amount_currency, to_currency)
            else:
                return m.company_currency_id.compute(move.debit - move.credit, to_currency)

        for one in self:
            date = self.env.context.get('date') or one.tba_id.date or fields.date.today()
            sale_currency = one.sale_currency_id
            move_lines = one.sale_invoice_id.move_line_ids
            amount_public1, amount_public2, amount_private1, amount_private2, amount_rmb3, amount_diff = 0, 0, 0, 0, 0, 0
            for move in move_lines:
                if move.account_id == account_public1:
                    amount_public1 += move.get_amount_to_currency(sale_currency, date=date)
                if move.account_id == account_public2:
                    amount_public2 += move.get_amount_to_currency(sale_currency, date=date)
                if move.account_id == account_private1:
                    amount_private1 += move.get_amount_to_currency(sale_currency, date=date)
                if move.account_id == account_private2:
                    amount_private2 += move.get_amount_to_currency(sale_currency, date=date)
                if move.account_id == account_rmb3:
                    amount_rmb3 += move.get_amount_to_currency(sale_currency, date=date)
                if move.account_id == account_diff:
                    amount_diff += move.get_amount_to_currency(sale_currency, date=date)
                # 计算预收款是收入在那个账户上
                if move.account_id.code == '2203':
                    # 获取订单上 根据分录明细，获取订单编号，获取对应预收科目变化
                    adv_account = move.so_id.advance_account_id
                    if adv_account == account_public1:
                        amount_public1 += move.get_amount_to_currency(sale_currency, date=date)
                    if adv_account == account_public2:
                        amount_public2 += move.get_amount_to_currency(sale_currency, date=date)
                    if adv_account == account_private1:
                        amount_private1 += move.get_amount_to_currency(sale_currency, date=date)
                    if adv_account == account_private2:
                        amount_private2 += move.get_amount_to_currency(sale_currency, date=date)

            amount_received = amount_public1 + amount_public2 + amount_private1 + amount_private2
            # print('>>>>>>>>>',  amount_public1, amount_public2, amount_private1, amount_private2, amount_diff )
            one.write({
                'amount_public1': amount_public1,
                'amount_public2': amount_public2,
                'amount_private1': amount_private1,
                'amount_private2': amount_private2,
                'amount_rmb3': amount_rmb3,
                'amount_diff': amount_diff,
                'amount_received': amount_received,
                'amount_real_payment': one.ciq_amount - amount_public2,
                'amount_account_payment': one.no_ciq_amount - amount_private1,
                'amount_account_adjust': amount_received - one.ciq_amount - one.no_ciq_amount
            })

    def update_supplier_invoice_date(self):
        line_obj = self.env['wizard.supplier.invoice_date.line']
        wizard = self.env['wizard.supplier.invoice_date'].create({})
        self.update_picking_date()

        for invoice in self.purchase_invoice_ids.filtered(lambda x: x.yjzy_type == 'purchase'):
            line_obj.create({
                'invoice_id': invoice.id,
                'wizard_id': wizard.id,
                'date': invoice.date_finish,
            })

        return {
            'name': '更新供应商发票日期',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.supplier.invoice_date',
            'res_id': wizard.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        # if not self.date_supplier_finish:
        #     raise Warning(u'请输入供应商交单日期')
        # invoices = self.purchase_invoice_ids.filtered(lambda x: x.yjzy_type == 'purchase')
        # invoices.write({'date_finish': self.date_supplier_finish})

    def update_picking_date(self):
        self.ensure_one()
        self.update_in_picking_date()
        self.update_out_picking_date()
        return True

    def update_in_picking_date(self):
        self.ensure_one()
        in_pickings = self.stage1picking_ids.filtered(lambda x: x.state == 'done')
        date_done = self.date_in or self.date_out_in
        if date_done:
            in_pickings.write({'date_done': date_done})

        if self.date_supplier_finish:
            in_pickings.write({'date_finish': self.date_supplier_finish})

    def update_out_picking_date(self):
        self.ensure_one()
        out_pickings = self.stage2picking_ids.filtered(lambda x: x.state == 'done')
        if self.date_out_in:
            out_pickings.write({'date_done': self.date_out_in})
        if self.date_customer_finish:
            out_pickings.write({'date_finish': self.date_customer_finish})
        if self.date_ship:
            out_pickings.write({'date_ship': self.date_ship})

    def compute_pack_data(self):
        self.ensure_one()
        pack_lines = self._crate_pack_lines()
        pack_lines.compute()

    def _crate_pack_lines(self):
        self.ensure_one()
        self.pack_line_ids.unlink()
        pack_line_obj = self.env['transport.pack.line']
        hs_name_dict = {}  # {'hs_name1': ['hscode', line_ids]}
        for line in self.line_ids:
            hs_name = line.product_id.hs_name
            hs_code = line.product_id.hs_code
            hs_en_name = line.product_id.hs_en_name

            if hs_name not in hs_name_dict:
                hs_name_dict[hs_name] = [hs_code, line, hs_en_name]
            else:
                hs_name_dict[hs_name][1] |= line
        pack_lines = pack_line_obj.browse([])
        for hs_name, data in list(hs_name_dict.items()):
            hs_code, lines, hs_en_name = data
            pack_line = pack_line_obj.create({
                'bill_id': self.id,
                'hs_code': hs_code,
                'hs_name': hs_name,
                'hs_en_name': hs_en_name,
                'line_ids': [(6, 0, [x.id for x in lines])],
                'sale_amount': sum([x.sale_amount for x in lines]),
            })
            pack_lines |= pack_line
        return pack_lines

    # 13ok
    def make_purchase_invoice(self):
        self.ensure_one()
        #     if not self.date_out_in:
        #          raise Warning(u'请先设置进仓日期')
        invoice_ids = []

        if not self.purchase_invoice_ids.filtered(lambda x: x.yjzy_type == 'purchase'):
            invoice_obj = self.env['account.invoice']
            purchase_orders = self.stage1move_ids.filtered(lambda x: x.state == 'done').mapped(
                'purchase_line_id').mapped('order_id')

            po_ctx = {'type': 'in_invoice', 'journal_type': 'purchase'}

            for partner in purchase_orders.mapped('partner_id'):
                invoice = invoice_obj.with_context(po_ctx).create({
                    'partner_id': partner.id,
                    'type': 'in_invoice',
                    'journal_type': 'purchase',
                    'date_ship': self.date_ship,
                    'date_finish': self.date_supplier_finish,
                    'bill_id': self.id,
                    'date_invoice': self.date_out_in,
                    'date': self.date_out_in,
                    # 'include_tax': x.include_tax,
                    'yjzy_type': 'purchase',
                    'yjzy_type_1': 'purchase',
                    'invoice_type_main': '10_main',
                    'invoice_attribute': 'normal',
                    'gongsi_id': self.purchase_gongsi_id.id,
                    'stage_id': self.env['account.invoice.stage'].search([('code', '=', '001')], limit=1).id,

                })
                invoice.clear_zero_line()
                invoice.yjzy_invoice_id = invoice.id
                invoice.invoice_attribute = 'normal'
                invoice.date_invoice = self.date_out_in

                for o in purchase_orders.filtered(lambda x: x.partner_id == partner):
                    invoice.purchase_id = o
                    invoice.purchase_order_change()
                    invoice.po_id = o
                    invoice.include_tax = o.include_tax

                # 确认发票
                invoice.compute_advance_pre_rest()
                invoice.action_invoice_open()
                invoice.make_plan_invoice_auto()  # 0518
                invoice_ids.append(invoice.id)


        else:
            invoice_ids = [x.id for x in self.purchase_invoice_ids]

        return {
            'name': '采购账单',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'tree_view_ref': 'account.invoice_tree',
            'domain': [('id', 'in', invoice_ids)]
        }

    def add_fee_outer(self, sale_invoices):
        invoice = sale_invoices[0]
        pdt = self.env.ref('yjzy_extend.product_fee_outer')
        invoice.invoice_line_ids[0].copy(default={
            'product_id': pdt.id,
            'name': pdt.name,
            'quantity': 1,
            'price_unit': self.fee_outer,
        })

    # 13ok
    def make_sale_invoice(self):
        self.ensure_one()
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        sale_invoice_ids = []
        if not self.sale_invoice_id:
            manual_qty_dic = {}
            for line in self.line_ids:
                moves = line.stage2move_ids.filtered(lambda x: x.state == 'done')
                qty = sum(x.product_uom_qty for x in moves)
                manual_qty_dic[line.sol_id.id] = qty
            sale_invoice_ids = self.so_ids.with_context({'manual_qty_dic': manual_qty_dic}).action_invoice_create()
            sale_invoices = invoice_obj.browse(sale_invoice_ids)
            if self.fee_outer_need:
                self.add_fee_outer(sale_invoices)
            for one in sale_invoices:
                for x in one.invoice_line_ids:
                    if one.type == 'out_refund' or one.type == 'in_refund':
                        x.yjzy_price_unit = -x.price_unit
                    else:
                        x.yjzy_price_unit = x.price_unit
                one.yjzy_invoice_id = one.id
                one.invoice_attribute = 'normal'
            sale_invoices.write({
                'date_invoice': self.date_out_in,
                'date_out_in': self.date_out_in,
                'date': self.date_out_in,
                'date_finish': self.date_customer_finish,
                'include_tax': self.include_tax,
                'date_ship': self.date_ship,
                'bill_id': self.id,
                'yjzy_type': 'sale',
                'yjzy_type_1': 'sale',
                'invoice_attribute': 'normal',
                'invoice_type_main': '10_main',
                'gongsi_id': self.gongsi_id.id,
                'stage_id': self.env['account.invoice.stage'].search([('code', '=', '001')], limit=1).id,
            })
            sale_invoices.compute_advance_pre_rest()
            # 比较实际出运金额和原始出运金额，根据差额来调整账单
            if self.sale_type == 'proxy':
                hsname_ids = self.hsname_ids
                total_amount = sum(x.amount for x in hsname_ids)
                total_actual_amount = sum(x.actual_amount for x in hsname_ids)
                diff_amount = total_actual_amount - total_amount
                if diff_amount != 0:
                    p_diff = self.env.ref('yjzy_extend.tb_diff_actual_amount')
                    invoice_line_obj.create({
                        'invoice_id': sale_invoices[0].id,
                        'product_id': p_diff.id,
                        'name': u'出运实际和原始差额',
                        'account_id': sale_invoices[0].invoice_line_ids[0].account_id.id,
                        'quantity': 1,
                        'uom_id': p_diff.uom_id.id,
                        'price_unit': diff_amount,
                    })

            # 发票明细添加运保费
            if self.fee_outer_need:
                p = self.env.ref('yjzy_extend.product_fee_outer')
                self.env['account.invoice.line'].create({
                    'invoice_id': sale_invoices[0].id,
                    'product_id': p.id,
                    'name': u'运保费',
                    'account_id': sale_invoices[0].invoice_line_ids[0].account_id.id,
                    'quantity': 1,
                    'uom_id': p.uom_id.id,
                    'price_unit': self.fee_outer,
                })
            sale_invoices[0].action_invoice_open()
            self.sale_invoice_id = sale_invoices[0]
        else:
            sale_invoice_ids = [self.sale_invoice_id.id]

        return {
            'name': '销售账单',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', sale_invoice_ids)]
        }

    @api.multi
    def write(self, vals):
        res = super(transport_bill, self).write(vals)
        need = set(['date_ship', 'date_supplier_finish', 'date_out_in', 'date_customer_finish']) & set(vals.keys())
        date_out_in = self.date_out_in
        print('===write need==', need)
        if need and date_out_in:
            if self.state not in (
                    'approve', 'confirmed', 'delivered', 'invoiced', 'finish_add_purchase', 'verifying', 'done'):
                raise Warning('非执行中的出运单，不允许填写日期')
            else:
                # 730 填写日期后，自动发货和生成账单，等待审批完成后过账
                # if self.state == 'approve':
                #     self.state = 'delivered'
                #     self.onece_all_stage()
                #     self.make_all_invoice()
                #     self.sync_data2invoice()
                # elif self.state in ('delivered','invoiced'):
                #       self.sync_data2invoice()
                if self.state in ('delivered', 'invoiced'):
                    self.sync_data2invoice()
            return res

    # akiny 发货的时候生成所有发票，填入进仓日期后，点生成应收应付按钮，完成确认。
    def sync_data2invoice(self):
        if not self.date_out_in:
            raise Warning(u'请先设置进仓日期')
        # for one in self:
        # 同步采购发票日期  akiny修改purchase_invoice_ids为all_purchase_invoice_ids
        for purchase_invoice in self.all_purchase_invoice_ids.filtered(lambda x: x.yjzy_type == 'purchase'):
            purchase_invoice.date_ship = self.date_ship
            # purchase_invoice.date_finish = one.date_supplier_finish
            purchase_invoice.date_invoice = self.date_out_in
            purchase_invoice.date = self.date_out_in
            purchase_invoice.date_out_in = self.date_out_in
            purchase_invoice._onchange_payment_term_date_invoice()
            # if purchase_invoice.state == 'draft':
            #     purchase_invoice.action_invoice_open()
        # 同步销售发票 akiny将sale_invoice_id更新为all_sale_invoice_ids
        # sale_invoice = one.sale_invoice_id
        # if sale_invoice:
        #     sale_invoice.date_invoice = one.date_out_in
        #     sale_invoice.date_out_in = one.date_out_in
        #     sale_invoice.date = one.date_out_in
        #     sale_invoice.date_finish = one.date_customer_finish
        #     sale_invoice.date_ship = one.date_ship
        #     sale_invoice._onchange_payment_term_date_invoice()
        #     # if sale_invoice.state == 'draft':
        #     #     sale_invoice.action_invoice_open()
        if self.all_sale_invoice_ids:
            for sale_invoice in self.all_sale_invoice_ids:
                sale_invoice.date_invoice = self.date_out_in
                sale_invoice.date_out_in = self.date_out_in
                sale_invoice.date = self.date_out_in
                sale_invoice.date_finish = self.date_customer_finish
                sale_invoice.date_ship = self.date_ship
                sale_invoice._onchange_payment_term_date_invoice()
        if self.all_back_tax_invoice_ids:
            for back_tax_invoice in self.all_back_tax_invoice_ids:
                back_tax_invoice.date_out_in = self.date_out_in
                back_tax_invoice.date_invoice = self.date_out_in
                back_tax_invoice.date = self.date_out_in
                back_tax_invoice.date_finish = self.date_customer_finish
                back_tax_invoice.date_ship = self.date_ship
                # 调用防范，更新到期日期。因为是onchange发票日期，如果不调用，到期日期就无法计算
                back_tax_invoice._onchange_payment_term_date_invoice()
        # back_tax_invoice = one.back_tax_invoice_id
        # if back_tax_invoice:
        #     back_tax_invoice.date_out_in = one.date_out_in
        #     back_tax_invoice.date_invoice = one.date_out_in
        #     back_tax_invoice.date = one.date_out_in
        #     back_tax_invoice.date_finish = one.date_customer_finish
        #     back_tax_invoice.date_ship = one.date_ship
        #     #调用防范，更新到期日期。因为是onchange发票日期，如果不调用，到期日期就无法计算
        #     back_tax_invoice._onchange_payment_term_date_invoice()
        # # back_tax_invoice = one.back_tax_invoice_id
        # # back_tax_invoice_sate = one.back_tax_invoice_id.state
        # # if back_tax_invoice and back_tax_invoice_sate == 'draft':
        # #     back_tax_invoice.action_invoice_open()
        # if one.date_all_state == 'done' and one.state == 'delivered':
        #     one.state = 'invoiced'
        return True

    def make_back_tax_invoice(self):
        self.ensure_one()
        # if not self.date_out_in:
        #     raise Warning(u'请先设置进仓日期')
        back_tax_invoice = self.back_tax_invoice_id
        if not back_tax_invoice:
            partner = self.env.ref('yjzy_extend.partner_back_tax')
            product = self.env.ref('yjzy_extend.product_back_tax')
            payment_term_id = self.env.ref('yjzy_extend.account_payment_term_back_tax_14days')
            # account = self.env['account.account'].search([('code','=', '50011'),('company_id', '=', self.user_id.company_id.id)], limit=1)
            account = product.property_account_income_id
            invoice_tenyale_name = 'tenyale_invoice'
            tenyale_name = self.env['ir.sequence'].next_by_code('account.invoice.%s' % invoice_tenyale_name)
            if not account:
                raise Warning(u'没有找到退税科目,请先在退税产品的收入科目上设置')
            if self.back_tax_amount != 0:
                back_tax_invoice = self.env['account.invoice'].create({
                    'tenyale_name': tenyale_name,
                    'partner_id': partner.id,
                    'type': 'out_invoice',
                    'journal_type': 'sale',
                    'date_ship': self.date,
                    'date_finish': self.date,
                    'bill_id': self.id,
                    'yjzy_type': 'back_tax',
                    'yjzy_type_1': 'back_tax',
                    'payment_term_id': payment_term_id.id,
                    'invoice_attribute': 'normal',
                    'invoice_type_main': '10_main',
                    'gongsi_id': self.purchase_gongsi_id.id,
                    'stage_id': self.env['account.invoice.stage'].search([('code', '=', '001')], limit=1).id,
                    'include_tax': self.include_tax,
                    'invoice_line_ids': [(0, 0, {
                        'name': '%s:%s' % (product.name, self.name),
                        'product_id': product.id,
                        'quantity': 1,
                        'price_unit': self.back_tax_amount,
                        'account_id': account.id,
                    })]
                })
                # 730 创建后直接过账

                back_tax_invoice.yjzy_invoice_id = back_tax_invoice.id
                back_tax_invoice.invoice_attribute = 'normal'
                back_tax_invoice.action_invoice_open()
                self.back_tax_invoice_id = back_tax_invoice
        return {
            'name': '退税账单',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'tree_view_ref': 'account.invoice_tree',
            'res_id': back_tax_invoice.id
        }

    # akiny 发货的时候生成所有发票，填入进仓日期后，点生成应收应付按钮，完成确认。
    def make_all_invoice(self):
        self.make_sale_invoice()
        self.make_purchase_invoice()
        self.make_back_tax_invoice()

    #  self.state = 'invoiced'

    # def unlink(self):
    #     for one in self:
    #         if one.state != 'cancel':
    #             raise Warning('不能删除非取消状态发运单')
    #     return super(transport_bill, self).unlink()

    def onece_all_stage(self):
        self.prepare_1_picking()
        self.process_1_picking()

        self.prepare_2_picking()
        self.process_2_picking()

        # 自动创建发票
        #  self.make_purchase_invoice()
        self.make_all_invoice()

    @api.onchange('date_project')
    def onchange_date_project(self):
        if not self.date:
            self.date = self.date_project

    @api.model
    def process_move_operation(self, move, lot, qty):
        move_line_obj = self.env['stock.move.line']
        move_line = move.move_line_ids and move.move_line_ids[0]
        if move_line:
            move_line.lot_id = lot.id
            move_line.qty_done = qty
        else:
            move_line = move_line_obj.create({
                'move_id': move.id,
                'product_id': move.product_id.id,
                'location_id': move.location_id.id,
                'location_dest_id': move.location_dest_id.id,
                # 'lot_name': pol.order_id.name,
                'lot_id': lot.id,
                'product_uom_qty': qty,
                'qty_done': qty,
                'product_uom_id': move.product_id.uom_id.id,
            })
        return move_line

    def check(self):
        self.ensure_one()
        for bill_line in self.line_ids:
            if bill_line.qty1stage <= 0:
                raise Warning('%s 入库数量不能小于0' % bill_line.name)

    # 13ok
    def clean_moves(self):
        self.move_ids = False
        # self.line_ids._clean_moves()

    # 13ok
    def prepare_1_picking(self):
        self.ensure_one()
        self.line_ids._prepare_1_picking()
        self.stage1state = 'confirmed'
        return True

    # 13ok
    def prepare_2_picking(self):
        self.ensure_one()
        self.line_ids._prepare_2_picking()
        self.stage2state = 'confirmed'
        return True

    def new_prepare_2_picking(self):
        self.ensure_one()
        self.line_ids._new_prepare_2_picking()
        self.stage2state = 'confirmed'
        return True

    # def prepare_3_picking(self):
    #     self.ensure_one()
    #     self.line_ids._prepare_3_picking()
    #     self.stage3state = 'confirmed'
    #     return True
    # 13ok
    def process_1_picking(self):
        self.ensure_one()
        todo_pickings = self.stage1picking_ids.filtered(lambda x: x.state == 'assigned')
        if todo_pickings:
            for todo_pick in todo_pickings:
                todo_pick.action_done()
            self.stage1state = 'done'
        return True

    # 13ok
    def process_2_picking(self):
        self.ensure_one()
        todo_pickings = self.stage2picking_ids.filtered(lambda x: x.state == 'assigned')
        if todo_pickings:
            for todo_pick in todo_pickings:
                for move in todo_pick.move_lines:
                    # move.quantity_done = move.reserved_availability
                    for mline in move.move_line_ids:
                        mline.qty_done = mline.product_uom_qty
                todo_pick.action_done()
            self.stage2state = 'done'
        return True

    # def process_3_picking(self):
    #     self.ensure_one()
    #     todo_pickings = self.stage3picking_ids.filtered(lambda x: x.state == 'assigned')
    #     if todo_pickings:
    #         todo_pickings.action_done()
    #         self.stage3state = 'done'
    #     return True
    # 13ok
    @api.constrains('line_ids')
    def check_lines(self):
        print('----------check_lines---------')

        if len(self.line_ids.mapped('so_id').mapped('partner_id')) > 1:
            raise Warning('发运单只允许关联一个客户的销售订单')

        if len(self.line_ids) != len(self.line_ids.mapped('sol_id')):
            raise Warning('出运明细有重复的销售明细行')

    # 13ok
    def open_wizard_transport4sol(self):
        war = ''
        # if not self.date:
        #     war += '请填写出运日期\n'
        if not self.date_project:
            war += '请填写出运日期\n'
        if self.current_date_rate == 0:
            war += '单日汇率不为零\n'
        if war:
            raise Warning(war)
        else:
            self.ensure_one()
            ctx = self.env.context.copy()
            ctx.update({
                'default_partner_id': self.partner_id.id,
                'default_gongsi_id': self.gongsi_id.id,
                'default_purchase_gongsi_id': self.purchase_gongsi_id.id,
                'add_sol': True,
            })
            return {
                'name': '添加销售明细',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'wizard.transport4so',
                # 'res_id': bill.id,
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': ctx,
            }

    # 13ok
    def open_wizard_transport4so(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx.update({
            'default_partner_id': self.partner_id.id,
            'default_gongsi_id': self.gongsi_id.id,
            'default_purchase_gongsi_id': self.purchase_gongsi_id.id,
            'add_so': True,
        })
        return {
            'name': '添加销售订单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.transport4so',
            # 'res_id': bill.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': ctx,
        }

    # 13ok
    def make_default_lot_plan(self):
        self.ensure_one()
        self.line_ids.make_default_lot_plan()
        self.is_done_plan = True

    def open_account_payment(self):
        ctx = self.env.context.copy()
        ctx.update({'default_payment_type': 'transfer'})
        return {
            'name': '付款单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment',
            # 'res_id': bill.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': ctx,
        }

    def create_qingguan_lines(self):
        self.ensure_one()
        self.qingguan_line_ids.unlink()
        qingguan_obj = self.env['transport.qingguan.line']
        product_dic = {}  # {pi*100+soid: }

        for i in self.line_ids:
            total = i.sol_id.price_unit * i.qty2stage_new * (1 - (i.discount or 0.0) / 100)
            total_origin = i.sol_id.price_unit * i.qty2stage_new
            pdt = i.product_id

            k = pdt.id * 100000 + i.so_id.id

            if k in product_dic:
                product_dic[k]['qty'] += i.qty2stage_new
                product_dic[k]['sub_total'] += total
                product_dic[k]['sub_total_origin'] += total_origin
            else:
                product_dic[k] = {'qty': i.qty2stage_new, 'sub_total': total, 'sub_total_origin': total_origin,
                                  'product_id': pdt.id, 'so_id': i.so_id.id, 's_uom_id': pdt.s_uom_id.id}

        for kk, data in list(product_dic.items()):
            line = qingguan_obj.create({
                'tb_id': self.id,
                'product_id': data['product_id'],
                's_uom_id': data['s_uom_id'],
                'so_id': data['so_id'],
                'qty': data['qty'],
                'sub_total': data['sub_total'],
                'sub_total_origin': data['sub_total_origin'],
                'price': data['sub_total'] / (data['qty'] or 1),
                'price_origin': data['sub_total_origin'] / (data['qty'] or 1),
            })

            # print('>>', line)
            line.compute_info()
        self.qingguan_state = 'done'
        # self.split_tuopan_weight_qingguan()

    def get_product_total(self):
        self.ensure_one()
        return sum([x.qty2stage_new for x in self.line_ids])

    def get_amount_word(self):
        x = num2words(round(self.sale_amount, 2)).upper()
        return x

    def open_sale_invoice(self):
        self.ensure_one()
        form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form_in_one')
        tree_view = self.env.ref('yjzy_extend.invoice_new_main_tree')
        return {
            'name': u'客户应收',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('id', 'in', [self.sale_invoice_id.id])]
        }

    def open_sale_invoice_new(self):
        self.ensure_one()
        form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.invoice_new_1_tree')
        return {
            'name': u'客户应收',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('id', 'in', [self.sale_invoice_id.id])],
            'target': 'new'
        }

    def open_purchase_invoice(self):
        form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form_in_one')
        tree_view = self.env.ref('yjzy_extend.invoice_new_supplier_1_tree')
        self.ensure_one()
        return {
            'name': u'供应商应付',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [
                ('id', 'in', [x.id for x in self.purchase_invoice_ids.filtered(lambda x: x.yjzy_type == 'purchase')])]

        }

    def open_purchase_invoice_new(self):
        form_view = self.env.ref('yjzy_extend.view_account_supplier_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.invoice_new_supplier_1_tree')
        self.ensure_one()
        return {
            'name': u'供应商应付',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [
                ('id', 'in', [x.id for x in self.purchase_invoice_ids.filtered(lambda x: x.yjzy_type == 'purchase')])],
            'target': 'new'
        }

    def open_purchase_invoice_1(self):
        form_view = self.env.ref('yjzy_extend.view_account_supplier_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.view_account_invoice_new_tree')
        self.ensure_one()
        return {
            'name': u'供应商日期填制',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [
                ('id', 'in', [x.id for x in self.purchase_invoice_ids.filtered(lambda x: x.yjzy_type == 'purchase')])],
            'target': 'new'
        }

    def open_transport_self(self):
        xml_id = self.env.context.get('form_xml_id')
        name = self.env.context.get('name')
        form = self.env.ref(xml_id)
        self.ensure_one()
        return {
            'name': name,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'transport.bill',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            "view_id": form.id,
            'target': 'new'
        }

    def open_transport_date_1(self):
        xml_id = self.env.context.get('form_xml_id')
        form = self.env.ref(xml_id)
        self.ensure_one()
        return {
            'name': u'附件',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'trans.date.attachment',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', [self.date_out_in_att_new.id])],
            'tree_view_ref': 'yjzy_extend.view_trans_date_attachment_tree',
            'target': 'new'
        }

    def open_back_tax_invoice(self):
        form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form_in_one')
        tree_view = self.env.ref('yjzy_extend.invoice_new_back_tax_tree')
        self.ensure_one()
        return {
            'name': '销售发票',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('id', 'in', [self.back_tax_invoice_id.id])]
        }

    def action_transport_bill_vendor_report(self):
        return self.env.ref('yjzy_extend.action_report_transport_bill_vendor').report_action(self.tb_vendor_ids)

    @api.model
    def cron_update_contract_type(self):
        print('=cron_update_rate==')

        for one in self:
            print('===', one)
            one.contract_type = one.partner_id.contract_type

    def cron_update_gongsi_id(self):
        print('=cron_update_rate==')

        for one in self:
            print('===', one)
            one.gongsi_id = one.company_id.gongsi_id
            one.purchase_gongsi_id = one.company_id.gongsi_id

    # akiny 新增
    @api.multi
    def print_qingguan_invoice(self):
        if not self.qingguan_line_ids:
            raise Warning('请先生成清关资料')
        return self.env.ref('yjzy_extend.action_report_transport_bill_invoice').report_action(self)

    @api.multi
    def print_qingguan_packing_list(self):
        if not self.qingguan_line_ids:
            raise Warning('请先生成清关资料')
        return self.env.ref('yjzy_extend.action_report_transport_bill_packing').report_action(self)

    @api.multi
    def print_bg_contract(self):
        if not self.qingguan_line_ids:
            raise Warning('请先生成报关明细')
        return self.env.ref('yjzy_extend.action_report_transport_bill_bgzl_contract').report_action(self)

    @api.multi
    def print_bg_invoice(self):
        if not self.qingguan_line_ids:
            raise Warning('请先生成报关明细')
        return self.env.ref('yjzy_extend.action_report_transport_bill_bgzl_invoice').report_action(self)

    @api.multi
    def print_bg_packing_list(self):
        if not self.qingguan_line_ids:
            raise Warning('请先生成报关明细')
        return self.env.ref('yjzy_extend.action_report_transport_bill_bgzl_packing').report_action(self)

    @api.multi
    def print_bgd(self):
        if not self.qingguan_line_ids:
            raise Warning('请先生成报关明细')
        return self.env.ref('yjzy_extend.action_report_transport_bill_bgzl_bgd').report_action(self)

    @api.multi
    def print_cost(self):
        return self.env.ref('yjzy_extend.action_report_sale_order_cost').report_action(self)

    def open_transport_bill_clearance(self):
        """ Utility method used to add an "Open Parent" button in partner views """
        self.ensure_one()
        clearance_form_id = self.env.ref('yjzy_extend.view_transport_bill_clearance_form').id
        return {
            'name': _(u'清关资料'),
            'view_type': 'form',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'transport.bill',
            'views': [(clearance_form_id, 'form')],
            'res_id': self.id,
            'target': 'current',
            'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }

    def open_transport_bill_supplier(self):
        """ Utility method used to add an "Open Parent" button in partner views """
        self.ensure_one()
        declare_form_id = self.env.ref('yjzy_extend.view_transport_bill_supplier_from').id
        return {
            'name': u'发货通知单',
            'view_type': 'form',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'transport.bill',
            'views': [(declare_form_id, 'form')],
            'res_id': self.id,
            'target': 'current',
            'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }

    def open_transport_bill_delivery(self):
        """ Utility method used to add an "Open Parent" button in partner views """
        self.ensure_one()
        return {
            'name': _(u'供应商发货通知单'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window',
            'res_model': 'transport.bill.vendor',
            'domain': [('id', 'in', [x.id for x in self.tb_vendor_ids])]
        }

    def open_transport_bill_declare(self):
        """ Utility method used to add an "Open Parent" button in partner views """
        self.ensure_one()
        declare_form_id = self.env.ref('yjzy_extend.view_transport_bill_declare_form').id
        return {
            'name': _(u'报关资料'),
            'view_type': 'form',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'transport.bill',
            'views': [(declare_form_id, 'form')],
            'res_id': self.id,
            'target': 'current',
            'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }

    def _stage_find(self, domain=None, order='sequence'):
        search_domain = list(domain)
        return self.env['transport.bill.stage'].search(search_domain, order=order, limit=1)

    def action_submit(self):
        if (self.org_real_sale_amount_new == self.org_hsname_actual_amount and self.sale_type != 'proxy') or (
                self.sale_type == 'proxy'):
            war = ''
            # if self.create_uid != self.env.user:
            #     raise Warning('您没有权限提交')
            # else:
            if self.ref and self.partner_id and self.date_project and self.incoterm and self.current_date_rate > 0 and \
                    self.payment_term_id and self.line_ids and self.sale_currency_id:
                so_id = self.line_ids.mapped('so_id')
                for so in so_id:
                    so.order_line_compute_project_tb_qty()
                self.amount_all()
                stage_id = self._stage_find(domain=[('code', '=', '002')])
                return self.write({'stage_id': stage_id.id,
                                   # 'state': 'submit',
                                   'submit_uid': self.env.user.id,
                                   'submit_date': fields.datetime.now()})
            else:
                if not self.ref:
                    war += '合同号不为空\n'
                if not self.partner_id:
                    war += '客户不为空\n'
                # if not self.date:
                #     war += '出运日期不为空\n'
                if not self.date_project:
                    war += '出运日期不为空\n'
                if not self.incoterm:
                    war += '价格条款不为空\n'
                if not self.payment_term_id:
                    war += '付款条款不为空\n'
                if not self.sale_currency_id:
                    war += '交易货币不为空\n'
                if self.current_date_rate <= 0:
                    war += '当日汇率不为0\n'
                if not self.line_ids:
                    war += '出运明细不为空\n'
                if war:
                    raise Warning(war)
        else:
            raise Warning('原始出运金额和实际出运金额不相同')

    def action_sales_approve(self):
        ##self.compute_pack_data()
        # self.create_qingguan_lines()
        # self.make_tb_vendor()
        stage_id = self._stage_find(domain=[('code', '=', '003')])
        stage_preview = self.stage_id
        user = self.env.user
        # group = self.env.user.groups_id
        if user not in stage_preview.user_ids:
            raise Warning('您没有权限审批')
        else:
            so_id = self.line_ids.mapped('so_id')
            for so in so_id:
                so.order_line_compute_project_tb_qty()
            self.write({'sales_confirm_uid': self.env.user.id,
                        'sales_confirm_date': fields.datetime.now(),
                        # 'state':'sales_approve',
                        'stage_id': stage_id.id})

    def action_approve(self):
        if (self.org_sale_amount == self.org_real_sale_amount and self.sale_type != 'proxy') or (
                self.sale_type == 'proxy'):
            stage_id = self._stage_find(domain=[('code', '=', '004')])
            so_id = self.line_ids.mapped('so_id')
            stage_preview = self.stage_id
            user = self.env.user
            # group = self.env.user.groups_id
            if user not in stage_preview.user_ids:
                raise Warning('您没有权限审批')
            else:
                for so in so_id:
                    if so.state == 'approve':
                        # so.action_confirm()
                        so.action_confirm_stage()

                self.write({'approve_uid': self.env.user.id,
                            'approve_date': fields.datetime.now(),
                            # 'state':'approve',
                            'stage_id': stage_id.id})
                self.compute_second_state()
                self.create_hsname_all_ids()
                self.make_new_order_track_tb()
                self.create_tb_po_line_ids()

        else:
            raise Warning('销售金额和原始销售不相等')

    def action_approve_new_stage(self):
        if (self.org_sale_amount == self.org_real_sale_amount and self.sale_type != 'proxy') or (
                self.sale_type == 'proxy'):
            stage_id = self._stage_find(domain=[('code', '=', '004')])
            so_id = self.line_ids.mapped('so_id')
            for so in so_id:
                if so.state == 'approve':
                    # so.action_confirm()
                    so.action_confirm_stage()  # 等待更新
                    # so.order_line_compute_project_tb_qty()
            stage_preview = self.stage_id
            user = self.env.user
            # group = self.env.user.groups_id
            if user not in stage_preview.user_ids:
                raise Warning('您没有权限审批')
            else:
                self.write({'approve_uid': self.env.user.id,
                            'approve_date': fields.datetime.now(),
                            # 'state':'approve',
                            'stage_id': stage_id.id})
                self.compute_second_state()
                self.create_hsname_all_ids()
        else:
            raise Warning('销售金额和原始销售不相等')

    def action_to_manager_approve(self):
        if (self.org_sale_amount == self.org_real_sale_amount and self.sale_type != 'proxy') or (
                self.sale_type == 'proxy'):
            stage_id = self._stage_find(domain=[('code', '=', '011')])
            stage_preview = self.stage_id
            user = self.env.user
            # group = self.env.user.groups_id
            if user not in stage_preview.user_ids:
                raise Warning('您没有权限审批')
            else:

                self.write({  # 'approve_uid':self.env.user.id,
                    # 'approve_date':fields.datetime.now(),
                    # 'state':'approve',
                    'stage_id': stage_id.id})
                self.compute_second_state()
        else:
            raise Warning('销售金额和原始销售不相等')

    def action_manager_approve(self):
        if (self.org_sale_amount == self.org_real_sale_amount and self.sale_type != 'proxy') or (
                self.sale_type == 'proxy'):
            stage_id = self._stage_find(domain=[('code', '=', '004')])
            stage_preview = self.stage_id
            user = self.env.user
            so_id = self.line_ids.mapped('so_id')
            for so in so_id:
                if so.sate == 'approve':
                    so.action_confirm()
            # group = self.env.user.groups_id
            if user not in stage_preview.user_ids:
                raise Warning('您没有权限审批')
            else:
                self.write({'approve_uid': self.env.user.id,
                            'approve_date': fields.datetime.now(),
                            # 'state':'approve',
                            'stage_id': stage_id.id})
        else:
            raise Warning('销售金额和原始销售不相等')

    # akiny
    def action_invoiced(self):
        user = self.env.user
        self.onece_all_stage()
        stage_id = self._stage_find(domain=[('code', '=', '005')])
        return self.write({  # 'state': 'invoiced',
            'invoiced_date': fields.datetime.now(),
            'invoiced_uid': user.id,
            'delivered_date': fields.datetime.now(),
            'delivered_uid': user.id,
            'stage_id': stage_id.id
        })

    # 阶段审批典型案例
    def action_refuse(self, reason):
        stage_id = self._stage_find(domain=[('code', '=', '009')])
        stage_preview = self.stage_id
        user = self.env.user
        group = self.env.user.groups_id
        if user not in stage_preview.user_ids:
            raise Warning('您没有权限拒绝')
        else:
            self.write({'submit_uid': False,
                        'submit_date': False,
                        'sales_confirm_uid': False,
                        'sales_confirm_date': False,
                        'approve_uid': False,
                        'approve_date': False,
                        'confirmed_uid': False,
                        'confirmed_date': False,
                        'invoiced_uid': False,
                        'invoiced_date': False,
                        # 'state': 'refused',
                        'stage_id': stage_id.id, })
        for tb in self:
            tb.message_post_with_view('yjzy_extend.transport_template_refuse_reason',
                                      values={'reason': reason, 'name': self.ref},
                                      subtype_id=self.env.ref(
                                          'mail.mt_note').id)  # 定义了留言消息的模板，其他都可以参考，还可以继续参考费用发送计划以及邮件方式

    def action_cancel(self):
        stage_id = self._stage_find(domain=[('code', '=', '010')])
        # self.budget_ids.unlink()
        self.write({'submit_uid': False,
                    'submit_date': False,
                    'sales_confirm_uid': False,
                    'sales_confirm_date': False,
                    'approve_uid': False,
                    'approve_date': False,
                    'confirmed_uid': False,
                    'confirmed_date': False,
                    'invoiced_uid': False,
                    'invoiced_date': False,
                    # 'state': 'cancel',
                    'stage_id': stage_id.id})

    def action_draft(self):
        stage_id = self._stage_find(domain=[('code', '=', '001')])
        # budget = self.env['budget.budget'].create({
        #     'type': 'transport',
        #     'tb_id': self.id,
        # })
        self.write({  # 'state': 'draft',
            'stage_id': stage_id.id})

    def confirmed2locked(self):
        self.state = 'locked'

    def action_done(self):
        self.state = 'done'

    # 失效
    def update_hexiaotype_doing_type(self):
        for one in self:
            print('---', one)
            hexiao_type = False
            state = one.state
            today = datetime.now()
            date_out_in = one.date_out_in
            # 未发货，开始发货，待核销，已核销
            if one.state in ('invoiced', 'verifying'):
                if (
                        one.sale_invoice_balance_new != 0 or one.purchase_invoice_balance_new != 0 or one.back_tax_invoice_balance_new != 0) and \
                        date_out_in and date_out_in < (today - relativedelta(days=180)).strftime('%Y-%m-%d 00:00:00'):
                    hexiao_type = 'abnormal'
                    state = 'verifying'
                if one.sale_invoice_balance_new == 0 and one.purchase_invoice_balance_new == 0 and one.back_tax_invoice_balance_new == 0:
                    hexiao_type = 'write_off'
                    state = 'verifying'
                one.hexiao_type = hexiao_type
                one.state = state

    # qq1 执行中的分组情况
    @api.depends('sale_invoice_balance_new', 'purchase_invoice_balance_new', 'back_tax_invoice_balance_new')  # qq
    def update_hexiao_state(self):
        for one in self:
            print('---', one)
            stage_id = one.stage_id
            # 未发货，开始发货，待核销，已核销
            if one.state in ('invoiced', 'verifying'):
                if one.sale_invoice_balance_new == 0 and one.purchase_invoice_balance_new == 0 and one.back_tax_invoice_balance_new == 0:
                    stage_id = self._stage_find(domain=[('code', '=', '007')])
                one.stage_id = stage_id

    # state异常的判断和核销状态的判断   应该失效
    def update_hexiaotype_doing_type_new(self):
        for one in self:
            print('---', one)
            hexiao_type = False
            stage_id = one.stage_id
            state = one.state
            today = datetime.now()
            date_out_in = one.date_out_in
            # 未发货，开始发货，待核销，已核销
            if one.state in ('invoiced', 'verifying'):
                if (
                        one.sale_invoice_balance_new != 0 or one.purchase_invoice_balance_new != 0 or one.back_tax_invoice_balance_new != 0) and \
                        date_out_in and date_out_in < (today - relativedelta(days=180)).strftime('%Y-%m-%d 00:00:00'):
                    hexiao_type = 'abnormal'
                    stage_id = self._stage_find(domain=[('code', '=', '007')])
                    # state = 'abnormal'
                if one.sale_invoice_balance_new == 0 and one.purchase_invoice_balance_new == 0 and one.back_tax_invoice_balance_new == 0:
                    if hexiao_type == 'abnormal':
                        hexiao_type = 'abnormal'
                        stage_id = self._stage_find(domain=[('code', '=', '007')])
                        # state = 'verifying'
                    else:
                        hexiao_type = 'write_off'
                        stage_id = self._stage_find(domain=[('code', '=', '007')])
                        # state = 'verifying'
                one.hexiao_type = hexiao_type
                # one.state = state
                one.stage_id = stage_id

    # 自动计算出运开票状态和自动发票过账
    def auto_invoice_open(self):
        for one in self:
            default_times = 0
            if one.company_id.after_date_out_in_times:
                default_times = one.company_id.after_date_out_in_times
            today = datetime.now()
            strptime = datetime.strptime
            if one.date_out_in and one.date_out_in_state == 'done' and one.state == 'delivered' and one.invoice_state == 'draft':
                for purchase_invoice in one.purchase_invoice_ids.filtered(lambda x: x.yjzy_type == 'purchase'):
                    if purchase_invoice and purchase_invoice.state == 'draft' and purchase_invoice.date_out_in:
                        purchase_date_out_in_times = (today - strptime(purchase_invoice.date_out_in, DF)).days
                        print('--times--', purchase_date_out_in_times)
                        if default_times < purchase_date_out_in_times:
                            purchase_invoice.action_invoice_open()
                sale_invoice = one.sale_invoice_id
                if sale_invoice and sale_invoice.state == 'draft' and sale_invoice.date_out_in:
                    sale_date_out_in_times = (today - strptime(sale_invoice.date_out_in, DF)).days
                    if default_times < sale_date_out_in_times:
                        sale_invoice.action_invoice_open()
                back_tax_invoice = one.back_tax_invoice_id
                back_tax_invoice_state = one.back_tax_invoice_id.state
                if back_tax_invoice and back_tax_invoice_state == 'draft' and back_tax_invoice.date_out_in:
                    back_tax_date_out_in = (today - strptime(back_tax_invoice.date_out_in, DF)).days
                    if default_times < back_tax_date_out_in:
                        back_tax_invoice.action_invoice_open()
            if one.state == 'delivered' and one.invoice_state == 'open':
                one.state = 'invoiced'
        return True

    # 手动更新一下状态使用
    def update_state_to_invoiced_or_delivered(self):
        for one in self:
            if one.date_all_state == 'done' and one.state == 'delivered':
                one.state = 'invoiced'
            if one.date_all_state != 'done' and one.state == 'invoiced':
                one.state = 'delivered'

    def action_Warning(self):
        if self.partner_id.state != 'done':
            war = '客户正在审批中，请先完成客户的审批'
            raise Warning(war)
