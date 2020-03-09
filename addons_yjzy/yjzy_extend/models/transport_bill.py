# -*- coding: utf-8 -*-
from num2words import num2words
from odoo.addons import decimal_precision as dp
from odoo import models, fields, api, _
from odoo.exceptions import Warning


Stage_Status = [
    ('draft', '未开始'),
    ('confirmed', '就绪'),
    ('done', '完成'),
]
Stage_Status_Default = 'draft'


class transport_bill(models.Model):
    _name = 'transport.bill'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '发运单'
    _order = 'id desc'


    def compute_info(self):
        for one in self:
            if (not one.outer_currency_id) or (not one.sale_currency_id) or (not one.third_currency_id):
                #print(u'币种数据不全，不计算')
                continue
            one.invoice_in_ids = one.sale_invoice_id + one.back_tax_invoice_id
            moves = one.line_ids.mapped('move_ids')
            one.move_ids = moves
            one.stage1move_ids = moves.filtered(lambda x: x.picking_code == 'incoming')
            one.stage2move_ids = moves.filtered(lambda x: x.picking_code == 'outgoing')
            pickings = one.move_ids.mapped('picking_id')
            one.picking_ids = pickings
            one.stage1picking_ids = pickings.filtered(lambda x: x.picking_type_code == 'incoming')
            one.stage2picking_ids = pickings.filtered(lambda x: x.picking_type_code == 'outgoing')

            one.so_ids = one.line_ids.mapped('sol_id').mapped('order_id')

            one.po_ids = one.line_ids.mapped('lot_plan_ids').mapped('lot_id').mapped('po_id')
            one.purchase_invoice_count = len(one.purchase_invoice_ids.filtered(lambda x: x.yjzy_type == 'purchase'))
            one.sale_invoice_count = one.sale_invoice_id and 1 or 0
            one.back_tax_invoice_count = one.back_tax_invoice_id and 1 or 0


            #计算统计金额
            lines = one.line_ids
            if not lines: continue

            org_sale_amount, sale_amount = one._get_sale_amount(lines)
            org_real_sale_amount = sum([x.amount for x in one.hsname_ids])

            real_sale_amount = one.third_currency_id and one.sale_currency_id.compute(org_real_sale_amount, one.third_currency_id) or 0

            purchase_cost = one.company_currency_id.compute(sum(x.purchase_cost for x in lines), one.third_currency_id)
            fandian_amount = sum([x.fandian_amount for x in one.fandian_ids])   ##### 不含税）采购金额*返点比例，（含税）采购金额*0.87*返点比例

            stock_cost = one.company_currency_id.compute(sum(x.stock_cost for x in lines), one.third_currency_id)
            #back_tax_amount = one.company_currency_id.compute(sum(x.back_tax_amount for x in lines), one.third_currency_id)

            if one.cip_type != 'normal':
                back_tax_amount = 0
            else:
                back_tax_amount = one.company_currency_id.compute(sum(x.back_tax_amount2 for x in one.btls_hs_ids), one.third_currency_id)

            other_cost = one.company_currency_id.compute(one._get_other_cost(), one.third_currency_id)
            sale_commission_amount = real_sale_amount * one.sale_commission_ratio

            vat_diff_amount = 0
            if one.include_tax  and one.company_currency_id.name == 'CNY':
                vat_diff_amount = (sale_amount - purchase_cost -stock_cost)/ 1.13 * 0.13

            profit_amount = real_sale_amount - purchase_cost - stock_cost - other_cost - vat_diff_amount - sale_commission_amount + back_tax_amount

            one.shoukuan_amount = one.sale_invoice_id.amount_total - one.sale_invoice_id.residual_signed
            one.fukuan_amount = sum([i.amount_total - i.residual_signed for i in one.purchase_invoice_ids.filtered(lambda x: x.yjzy_type == 'purchase')]) #（采购发票line.合计金额 - 到期金额）

            budget_amount = one.fee_inner + one.fee_rmb1 + one.fee_rmb2
            budget_reset_amount = budget_amount - sum([x.total_amount for x in one.expense_ids])

            one.org_sale_amount = org_sale_amount
            one.org_real_sale_amount = org_real_sale_amount
            one.sale_amount = sale_amount
            one.real_sale_amount = real_sale_amount
            one.sale_commission_amount = sale_commission_amount
            one.stock_cost = stock_cost
            one.purchase_cost = purchase_cost
            one.other_cost = other_cost
            one.back_tax_amount = back_tax_amount
            one.profit_amount = profit_amount
            one.fandian_amount = fandian_amount
            one.budget_amount = budget_amount
            one.budget_reset_amount = budget_reset_amount


            ###profit_ratio_base = (one.sale_amount - one.get_outer())
            one.profit_ratio = one.sale_amount != 0.0 and one.profit_amount / one.sale_amount or 0


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

    def _get_sale_amount(self, lines):
        """
        return:  org_sale_amount:sale_currency   sale_amount: third_currency
        line: sale_amount：company_currency_id， org_currency_sale_amount：sale_currency_id
        """
        sale_amount = sum( x.company_currency_id.compute(x.sale_amount, self.third_currency_id) for x in lines)
        org_sale_amount = sum(x.org_currency_sale_amount for x in lines)

        if self.fee_outer_need:
            org_sale_amount += self.outer_currency_id.compute(self.fee_outer, self.sale_currency_id)
            sale_amount += self.outer_currency_id.compute(self.fee_outer, self.third_currency_id)
        return org_sale_amount, sale_amount

    def _get_sale_commission(self, sale_amount):
        sale_commission_ratio = float(
            self.env['ir.config_parameter'].sudo().get_param('addons_yjzy.sale_commission', '0.015'))
        return sale_commission_ratio, sale_amount * sale_commission_ratio

    def _get_other_cost(self):
        return sum([self.fee_inner, self.fee_rmb1, self.fee_rmb2,
                    self.outer_currency_id.compute(self.fee_outer, self.company_currency_id),
                    self.export_insurance_currency_id.compute(self.fee_export_insurance, self.company_currency_id),
                    self.other_currency_id.compute(self.fee_other, self.company_currency_id),
                    ])

    def compute_ciq_amount(self):
        for one in self:
            pack_lines = one.pack_line_ids
            one.ciq_amount = sum([x.amount2 for x in one.hsname_ids])
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
            sale_invoice = one.sale_invoice_id
            purchase_invoices = one.purchase_invoice_ids.filtered(lambda x: x.yjzy_type == 'purchase')
            back_tax_invoice = one.back_tax_invoice_id

            one.sale_invoice_total = sale_invoice.amount_total
            one.purhcase_invoice_total = sum([x.amount_total for x in purchase_invoices])
            one.back_tax_invoice_total = back_tax_invoice.amount_total
            one.sale_invoice_paid = sale_invoice.residual_signed
            one.purhcase_invoice_paid = sum([x.residual_signed for x in purchase_invoices])
            one.back_tax_invoice_paid = back_tax_invoice.residual_signed
            one.sale_invoice_balance = sale_invoice.amount_total - sale_invoice.residual_signed
            one.purhcase_invoice_balance = sum([x.residual_signed for x in purchase_invoices])
            one.back_tax_invoice_balance = back_tax_invoice.amount_total - sale_invoice.residual_signed


    # 货币设置
    state = fields.Selection([('cancel', u'取消'),('draft', '草稿'), ('w_sale_manager', u'待批准'), ('w_sale_director', u'待销售总监'),
                              ('confirmed', '审批完成'), ('locked', '单证审核'), ('done', '完成'), ('edit', u'可修改')], '状态',
                             default='draft', track_visibility='onchange',)
    locked = fields.Boolean(u'锁定不允许修改')
    include_tax = fields.Boolean(u'含税')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True, string='公司货币')
    company_currency_id = fields.Many2one('res.currency', string='公司货币', related='company_id.currency_id', readonly=True)
    sale_currency_id = fields.Many2one('res.currency', u'交易货币', required=True, store=True)
    third_currency_id = fields.Many2one('res.currency', u'统计货币', required=True,
                                        default=lambda self: self.env.user.company_id.currency_id.id)

    name = fields.Char('编号', default=lambda self: self.env['ir.sequence'].next_by_code('transport.bill'))
    ref = fields.Char(u'出运合同号')
    date = fields.Date(u'出运日期')
    exchange_rate = fields.Float(u'目前汇率', compute=compute_exchange_rate)
    tba_id = fields.Many2one('transport.bill.account', '转账调节单')

    partner_id = fields.Many2one('res.partner', '客户', required=True, domain=[('customer', '=', True)])
    user_id = fields.Many2one('res.users', u'业务员')
    partner_invoice_id = fields.Many2one('res.partner', string='发票地址', readonly=False, required=True)
    partner_shipping_id = fields.Many2one('res.partner', string='送货地址',  required=False)
    notice_man = fields.Char(u'通知人')
    delivery_man = fields.Char(u'发货人')
    production_sale_unit = fields.Char('生产销售单位')
    company_id = fields.Many2one('res.company', '公司', required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)

    tuopan_weight = fields.Float(u'托盘重量')
    tuopan_volume = fields.Float(u'托盘体积')

    so_ids = fields.Many2many('sale.order', 'ref_tb_so', 'so_id', 'tb_id', string='销售订单', compute=compute_info, store=False)
    po_ids = fields.Many2many('purchase.order', string='采购订单', compute=compute_info, store=False)

    cip_type = fields.Selection([('normal', u'正常报关'), ('buy', '买单报关'), ('none', '不报关')], string=u'报关', default='normal')
    line_ids = fields.One2many('transport.bill.line', 'bill_id', '明细', readonly=True, states={'draft': [('readonly', False)]})

    picking_ids = fields.Many2many('stock.picking', compute=compute_info, store=False, string='调拨')
    stage1picking_ids = fields.Many2many('stock.picking', compute=compute_info, store=False,
                                         domain=[('picking_type_code', '=', 'incoming')], string='入库')
    stage2picking_ids = fields.Many2many('stock.picking', compute=compute_info,
                                         domain=[('picking_type_code', '=', 'internal')], string='出库')

    move_ids = fields.Many2many('stock.move', string='库存移动详情', compute=compute_info)
    stage1move_ids = fields.Many2many('stock.move', string='入库明细', compute=compute_info)
    stage2move_ids = fields.Many2many('stock.move', string='发货明细', compute=compute_info)

    stage1state = fields.Selection(Stage_Status, '入库', default=Stage_Status_Default, readonly=True)
    stage2state = fields.Selection(Stage_Status, '出库', default=Stage_Status_Default, readonly=True)

    # 出运成本单据
    sale_commission_ratio = fields.Float('经营计提', digits=(2, 4),
                                         default=lambda self: self.env['ir.config_parameter'].sudo().get_param('addons_yjzy.sale_commission', '0.015'))
    incoterm = fields.Many2one('stock.incoterms', '贸易术语')
    incoterm_code = fields.Char('贸易术语', related='incoterm.code', readonly=True)
    org_sale_amount = fields.Monetary('销售金额', currency_field='sale_currency_id', compute=compute_info, digits=dp.get_precision('Money'))
    org_real_sale_amount = fields.Monetary('实际销售金额', currency_field='sale_currency_id', compute=compute_info, digits=dp.get_precision('Money'))

    #统计金额
    sale_amount = fields.Monetary('销售金额', currency_field='third_currency_id', compute=compute_info, digits=dp.get_precision('Money'))
    real_sale_amount = fields.Monetary('实际销售金额', currency_field='third_currency_id', compute=compute_info, digits=dp.get_precision('Money'))
    sale_commission_amount = fields.Monetary('经营计提金额', currency_field='third_currency_id', compute=compute_info)
    purchase_cost = fields.Monetary('采购成本', currency_field='third_currency_id', compute=compute_info, digits=dp.get_precision('Money'))
    fandian_amount = fields.Monetary('返点金额字', currency_field='third_currency_id', compute=compute_info, digits=dp.get_precision('Money'))
    stock_cost = fields.Monetary('库存成本', currency_field='third_currency_id', compute=compute_info, igits=dp.get_precision('Money'))
    other_cost = fields.Monetary('其他费用总计', currency_field='third_currency_id', compute=compute_info, igits=dp.get_precision('Money'))

    vat_diff_amount = fields.Monetary(u'增值税差额', currency_field='third_currency_id', compute=compute_info, digits=dp.get_precision('Money'))
    profit_amount = fields.Monetary('利润', currency_field='third_currency_id', compute=compute_info, igits=dp.get_precision('Money'))
    profit_ratio = fields.Float('利润率', digits=(2, 4), compute=compute_info)

    back_tax_amount = fields.Monetary('退税金额', currency_field='third_currency_id', compute=compute_info, digits=dp.get_precision('Money'))
    shoukuan_amount = fields.Monetary(u'收款金额', digits=(2, 4), compute=compute_info)
    fukuan_amount = fields.Monetary(u'付款金额', digits=(2, 4), compute=compute_info)

    budget_amount = fields.Monetary('预算', compute=compute_info, currency_field='company_currency_id')
    budget_reset_amount = fields.Monetary('预算剩余',  compute=compute_info, currency_field='company_currency_id')
    expense_ids = fields.One2many('hr.expense', 'tb_id', u'费用')

    sale_invoice_total = fields.Monetary(u'销售发票金额', compute=compute_invoice_amount)
    purhcase_invoice_total = fields.Monetary(u'采购发票金额', compute=compute_invoice_amount)
    back_tax_invoice_total = fields.Monetary(u'退税发票金额', compute=compute_invoice_amount)

    sale_invoice_paid = fields.Monetary(u'销售发票已付', compute=compute_invoice_amount)
    purhcase_invoice_paid = fields.Monetary(u'采购发票已付', compute=compute_invoice_amount)
    back_tax_invoice_paid = fields.Monetary(u'退税发票已付', compute=compute_invoice_amount)

    sale_invoice_balance = fields.Monetary(u'销售发票余额', compute=compute_invoice_amount, store=True)
    purhcase_invoice_balance = fields.Monetary(u'采购发票余额', compute=compute_invoice_amount, store=True)
    back_tax_invoice_balance = fields.Monetary(u'退税发票余额', compute=compute_invoice_amount, store=True)


    # 其他费用 fee_inner,fee_rmb1,fee_rmb2,fee_outer,fee_export_insurance,fee_other
    fee_inner = fields.Monetary('国内运杂费', currency_field='company_currency_id')
    fee_rmb1 = fields.Monetary('人民币费用1', currency_field='company_currency_id')
    fee_rmb2 = fields.Monetary('人民币费用2', currency_field='company_currency_id')

    fee_outer = fields.Monetary('国外运保费', currency_field='outer_currency_id')
    fee_outer_need = fields.Boolean(u'国外运保费计入应收', default=False)
    outer_currency_id = fields.Many2one('res.currency', '国外运保费货币', required=True )
    fee_export_insurance = fields.Monetary('出口保险费', currency_field='export_insurance_currency_id')
    export_insurance_currency_id = fields.Many2one('res.currency', '出口保险费货币')
    fee_other = fields.Monetary('其他外币费用', currency_field='other_currency_id')
    other_currency_id = fields.Many2one('res.currency', '其他外币费用货币')





    sale_type = fields.Selection([('inner', '自营'), ('export', '出口'), ('proxy', '代理')], '业务类型')
    account_type = fields.Selection([('tt', 'T/T'), ('lc', 'LC')], '收汇方式')
    credit_info = fields.Char('信用证信息')
    trans_type = fields.Selection([('sea', 'By SEA'), ('air', 'By AIR'), ('express', 'By Express'),('other', u'其他')], '运输方式')
    insurance_info = fields.Char('保险说明')
    description = fields.Text(u'发运说明')
    pack_line_ids = fields.One2many('transport.pack.line', 'bill_id', '装箱统计')
    pack_line_ids2 = fields.One2many('transport.pack.line', related='pack_line_ids')

    qingguan_description = fields.Html(u'清关描述')
    qingguan_line_ids = fields.One2many('transport.qingguan.line', 'tb_id', '清关明细')
    qingguan_state = fields.Selection([('draft', u'未统计'), ('done', u'已统计')], string=u'清关统计', default='draft')


    description_baoguan = fields.Html('报关合同说明')
    date_out_in = fields.Date('进仓日期')
    date_in = fields.Date('入库日期')
    date_ship = fields.Date('出运船日期')
    date_customer_finish = fields.Date('客户交单日期')
    date_supplier_finish = fields.Date('供应商交单确认日期')

    sale_invoice_id = fields.Many2one('account.invoice', '销售发票')
    purchase_invoice_ids = fields.One2many('account.invoice', 'bill_id', '采购发票')
    back_tax_invoice_id = fields.Many2one('account.invoice', '退税发票')
    sale_invoice_count = fields.Integer(u'销售发票数', compute=compute_info)
    purchase_invoice_count = fields.Integer(u'采购发票数', compute=compute_info)
    back_tax_invoice_count = fields.Integer(u'退税发票数', compute=compute_info)

    invoice_in_ids = fields.Many2many('account.invoice', u'发票汇总', compute=compute_info)


    #单证信息
    pallet_type = fields.Selection([('ctns', 'CTNS'),('plts', 'PLTS')], u'包装类型')
    pallet_qty = fields.Integer(u'托盘数')
    invoice_title = fields.Char('发票抬头')
    mark_ids = fields.Many2many('transport.mark', 'ref_mark_tbill',  'tid', 'mid' '唛头')
    partner_mark_comb_ids = fields.Many2many('mark.comb', related='partner_id.mark_comb_ids')
    mark_comb_id = fields.Many2one('mark.comb', u'唛头组')
    partner_notice_id = fields.Many2one('res.partner', '通知人')
    wharf_src_id = fields.Many2one('stock.wharf', '装船港')
    wharf_dest_id = fields.Many2one('stock.wharf', '目的港')
    payment_term_id = fields.Many2one('account.payment.term', string='付款条款')
    partner_country_id = fields.Many2one('res.country', '贸易国别')
    forwarder_name = fields.Char('货代公司')
    settlement = fields.Char('结算方式')
    notice = fields.Text('注意事项')
    demand_info = fields.Text(u'交单要求')

    #金额计算
    ciq_amount = fields.Monetary('报关金额', compute=compute_ciq_amount, currency_field='sale_currency_id', digits=dp.get_precision('Money'))
    no_ciq_amount = fields.Monetary('不报关金额', compute=compute_ciq_amount,  currency_field='company_currency_id')
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

    tbl_lot_ids = fields.One2many('bill.line.lot', 'tb_id', u'批次明细')
    tb_vendor_ids = fields.One2many('transport.bill.vendor', 'tb_id', u'供应商发运单')

    is_done_plan = fields.Boolean(u'默认调拨计划完成')
    is_done_tuopan = fields.Boolean(u'托盘分配完成')
    is_done_tb_vendor = fields.Boolean(u'供应商发运完成')

    sale_assistant_id = fields.Many2one('res.users', u'业务助理')
    is_editable = fields.Boolean(u'可编辑')




    @api.constrains('ref')
    def check_contract_code(self):
        for one in self:
            if self.search_count([('ref', '=', one.ref)]) > 1:
                raise Warning('出运合同号重复')


    @api.multi
    # def copy(self, default=None):
    #     self.ensure_one()
    #     default = dict(default or {})
    #     if 'ref' not in default:
    #         default['ref'] = "%s(copy)" % self.contract_code
    #     return super(transport_bill, self).copy(default)


    def unlink(self):
        for one in self:
            if one.state != 'cancel':
                raise Warning(u'只有取消状态允许删除')


        return super(transport_bill, self).unlink()

    def action_cancel(self):
        self.state = 'cancel'

    def action_draft(self):
        self.state = 'draft'


    @api.multi
    def name_get(self):
        ctx = self.env.context
        result = []
        for one in self:
            name = one.name
            if one.ref:
                name += ':%s' % one.ref
            result.append((one.id, name))
        return result

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


    def split_tuopan_weight(self):
        if  self.tuopan_weight <= 0 or self.tuopan_volume <=0:
            raise Warning(u'请先设置托盘重量和体积')

        qinguan_count = sum([x.qty for x in self.qingguan_line_ids])
        if qinguan_count > 0:
            for line in self.qingguan_line_ids:
                line.tuopan_weight = line.qty / qinguan_count * self.tuopan_weight

        hsl_count = sum([x.qty_max for x in self.hsname_ids])
        if hsl_count > 0:
            for line in self.hsname_ids:
                line.tuopan_weight = line.qty_max / hsl_count * self.tuopan_weight

        #================tuopan_volume
        qinguan_volume = sum([x.volume for x in self.qingguan_line_ids])
        if qinguan_volume > 0:
            for line in self.qingguan_line_ids:
                line.tuopan_volume = line.volume / qinguan_volume * self.tuopan_volume

        hsl_volume = sum([x.volume for x in self.hsname_ids])
        if hsl_volume > 0:
            for line in self.hsname_ids:
                line.tuopan_volume = line.volume / hsl_volume * self.tuopan_volume

        self.is_done_tuopan = True





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
        elif 'state' in init_values and self.state == 'locked':
            return 'yjzy_extend.mt_tb_locked'
        elif 'state' in init_values and self.state == 'done':
            return 'yjzy_extend.mt_tb_done'

        return super(transport_bill, self)._track_subtype(init_values)

    def action2w_sale_manager(self):
        ##self.compute_pack_data()
        #self.create_qingguan_lines()
        #self.make_tb_vendor()
        self.state = 'w_sale_manager'



    def action2w_sale_director(self):
        self.state = 'w_sale_director'

    def action2confirm(self):
        self.ensure_one()
        if not self.pack_line_ids:
            raise Warning('单证信息不全')
        if not self.qingguan_line_ids:
            raise Warning('清关信息不全')
        self.state = 'confirmed'

    def confirmed2locked(self):
        self.state = 'locked'

    def action_done(self):
        self.state = 'done'


    @api.onchange('partner_id')
    def onchange_partner(self):
        mans = self.partner_id.child_ids
        ship_man = mans.filtered(lambda x: x.type=='delivery')
        notice_man = mans.filtered(lambda x: x.type=='notice')
        addr = self.partner_id.address_get(['delivery', 'invoice'])

        values = {
            'partner_invoice_id': addr['invoice'],
            'partner_shipping_id': addr['delivery'],
        }

        self.partner_invoice_id = addr['invoice']
        self.partner_shipping_id = addr['delivery']
        self.invoice_title = self.partner_id.invoice_title
        self.mark_ids = self.partner_id.mark_ids
        self.partner_notice_id = notice_man and notice_man[0]
        self.wharf_src_id = self.partner_id.wharf_src_id
        self.wharf_dest_id = self.partner_id.wharf_dest_id
        self.payment_term_id = self.partner_id.property_payment_term_id
        self.partner_country_id = self.partner_id.country_id
        self.user_id = self.partner_id.user_id
        self.sale_currency_id = self.partner_id.property_product_pricelist.currency_id
        self.outer_currency_id = self.sale_currency_id
        self.notice_man = self.partner_id.notice_man
        self.delivery_man = self.partner_id.delivery_man
        self.demand_info  = self.partner_id.demand_info


    def make_tb_vendor(self):
        #print('>>>>make_tb_vendor')
        self.ensure_one()
        tbv_obj = self.env['transport.bill.vendor']
        self.tb_vendor_ids.unlink()
        plans =  self.line_ids.mapped('lot_plan_ids').filtered(lambda x: x.stage_1)
        suppliers = plans.mapped('lot_id').mapped('supplier_id')
        for supplier in suppliers:
            tbv = tbv_obj.create({
                'partner_id': supplier.id,
                'tb_id': self.id,
            })
            tbv.make_lines()
        self.is_done_tb_vendor = True


    def make_tbl_lot(self):
        for one in self:
            one.tbl_lot_ids = None
            #创建明细批次
            one.line_ids.compute_tbl_lot()
            #创建供应商发货单
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
        #print(('===========', res))
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
                #计算预收款是收入在那个账户上
                if move.account_id.code == '2203':
                    #获取订单上 根据分录明细，获取订单编号，获取对应预收科目变化
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
        hs_name_dict = {}   #{'hs_name1': ['hscode', line_ids]}
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
            hs_code,lines,hs_en_name = data
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

    def make_purchase_invoice(self):
        self.ensure_one()
        if not self.date_out_in:
            raise Warning(u'请先设置进仓日期')
        invoice_ids = []

        if not self.purchase_invoice_ids.filtered(lambda x: x.yjzy_type == 'purchase'):
            invoice_obj = self.env['account.invoice']
            purchase_orders = self.stage1move_ids.filtered(lambda x: x.state == 'done').mapped('purchase_line_id').mapped('order_id')

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
                    'include_tax': self.include_tax,
                    'yjzy_type': 'purchase',

                })
                invoice.clear_zero_line()

                invoice.date_invoice = self.date_out_in
                for o in purchase_orders.filtered(lambda x: x.partner_id == partner):
                    invoice.purchase_id = o
                    invoice.purchase_order_change()
                    invoice.po_id = o

                invoice_ids.append(invoice.id)
        else:
            invoice_ids = [x.id for x in self.purchase_invoice_ids]

        return {
            'name': '采购发票',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
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



    def make_sale_invoice(self):
        self.ensure_one()
        #print('===make_sale_invoice===1', self.so_ids)
        if not self.date_out_in:
            raise Warning(u'请先设置进仓日期')

        invoice_obj = self.env['account.invoice']
        sale_invoice_ids = []
        if not self.sale_invoice_id:
            manual_qty_dic = {}
            for line in self.line_ids:
                moves = line.stage2move_ids.filtered(lambda x: x.state == 'done')
                qty = sum(x.product_uom_qty for x in moves)
                manual_qty_dic[line.sol_id.id] = qty

            #print('===make_sale_invoice===', self.so_ids, manual_qty_dic)

            sale_invoice_ids = self.so_ids.with_context({'manual_qty_dic': manual_qty_dic}).action_invoice_create()
            sale_invoices = invoice_obj.browse(sale_invoice_ids)

            if self.fee_outer_need:
                self.add_fee_outer(sale_invoices)


            sale_invoices.write({
                'date_invoice': self.date_out_in,
                'date_finish': self.date_customer_finish,
                'include_tax': self.include_tax,
                'date_ship': self.date_ship,
                'bill_id': self.id,
                'yjzy_type': 'sale',
            })

            #发票明细添加运保费
            if self.fee_outer_need:
                p = self.env.ref('yjzy_extend.product_fee_outer')
                self.env['account.invoice.line'].create({
                    'invoice_id': sale_invoices[0].id,
                    'product_id': p.id,
                    'name': u'运保费',
                    'account_id': sale_invoices[0].invoice_line_ids[0].account_id.id,
                    'quantity':1,
                    'uom_id': p.uom_id.id,
                    'price_unit': self.fee_outer,
                })




            self.sale_invoice_id = sale_invoices[0]
        else:
            sale_invoice_ids = [self.sale_invoice_id.id]

        return {
            'name': '销售发票',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', sale_invoice_ids)]
        }

    def make_back_tax_invoice(self):
        self.ensure_one()
        if not self.date_out_in:
            raise Warning(u'请先设置进仓日期')
        back_tax_invoice = self.back_tax_invoice_id
        if not back_tax_invoice:
            partner =  self.env.ref('yjzy_extend.partner_back_tax')
            product = self.env.ref('yjzy_extend.product_back_tax')
            #account = self.env['account.account'].search([('code','=', '50011'),('company_id', '=', self.user_id.company_id.id)], limit=1)
            account = product.property_account_income_id

            if not account:
                raise Warning(u'没有找到退税科目,请先在退税产品的收入科目上设置')

            back_tax_invoice =  self.env['account.invoice'].create({
                'partner_id': partner.id,
                'type': 'out_invoice',
                'journal_type': 'sale',
                'date_ship': self.date,
                'date_finish': self.date,
                'bill_id': self.id,
                'yjzy_type': 'back_tax',


                'include_tax': self.include_tax,
                'invoice_line_ids': [(0, 0, {
                    'name': '%s:%s' % (product.name, self.name),
                    'product_id': product.id,
                    'quantity': 1,
                    'price_unit': self.back_tax_amount,
                    'account_id': account.id,
                })]
            })
            self.back_tax_invoice_id = back_tax_invoice
        return {
            'name': '退税发票',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'res_id': back_tax_invoice.id
        }

    def unlink(self):
        for one in self:
            if one.state != 'draft':
                raise Warning('不能删除非草稿发运单')
        return super(transport_bill, self).unlink()

    def onece_all_stage(self):
        self.prepare_1_picking()
        self.process_1_picking()
        self.prepare_2_picking()
        self.process_2_picking()

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

    def clean_moves(self):
        self.move_ids = False
        # self.line_ids._clean_moves()

    def prepare_1_picking(self):
        self.ensure_one()
        self.line_ids._prepare_1_picking()
        self.stage1state = 'confirmed'
        return True

    def prepare_2_picking(self):
        self.ensure_one()
        self.line_ids._prepare_2_picking()
        self.stage2state = 'confirmed'
        return True

    # def prepare_3_picking(self):
    #     self.ensure_one()
    #     self.line_ids._prepare_3_picking()
    #     self.stage3state = 'confirmed'
    #     return True

    def process_1_picking(self):
        self.ensure_one()
        todo_pickings = self.stage1picking_ids.filtered(lambda x: x.state == 'assigned')
        if todo_pickings:
            for todo_pick in todo_pickings:
                todo_pick.action_done()
            self.stage1state = 'done'
        return True

    def process_2_picking(self):
        self.ensure_one()
        todo_pickings = self.stage2picking_ids.filtered(lambda x: x.state == 'assigned')
        if todo_pickings:
            for todo_pick in todo_pickings:
                for move in todo_pick.move_lines:
                    #move.quantity_done = move.reserved_availability
                    for mline in move.move_line_ids:
                        mline.qty_done  = mline.product_uom_qty
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

    @api.constrains('line_ids')
    def check_lines(self):
        if len(self.line_ids.mapped('so_id').mapped('partner_id')) > 1:
            raise Warning('发运单只允许关联一个客户的销售订单')

    def open_wizard_transport4so(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx.update({'default_partner_id': self.partner_id.id})
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

    def make_default_lot_plan(self):
        self.ensure_one()
        self.line_ids._make_default_lot_plan()
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
        product_dic = {}   #{pi*100+soid: }
        for i in self.line_ids:
            total = i.sol_id.price_unit * i.qty2stage
            pdt = i.product_id

            k = pdt.id * 100000 + i.so_id.id

            if k in product_dic:
                product_dic[k]['qty'] += i.qty2stage
                product_dic[k]['sub_total'] += total
            else:
                product_dic[k] = {'qty': i.qty2stage, 'sub_total': total, 'product_id': pdt.id, 'so_id': i.so_id.id, 's_uom_id': pdt.s_uom_id.id}

        for kk, data in list(product_dic.items()):
            line = qingguan_obj.create({
                'tb_id': self.id,
                'product_id': data['product_id'],
                's_uom_id': data['s_uom_id'],
                'so_id': data['so_id'],
                'qty': data['qty'],
                'sub_total': data['sub_total'],
                'price': data['sub_total'] / (data['qty'] or 1),
            })
            #print('>>', line)
            line.compute_info()
        self.qingguan_state = 'done'


    def get_product_total(self):
        self.ensure_one()
        return sum([x.qty2stage for x in self.line_ids])

    def get_amount_word(self):
        x = num2words(round(self.sale_amount, 2)).upper()
        return x

    def open_sale_invoice(self):
        self.ensure_one()
        form_view = self.env.ref('account.invoice_form')
        tree_view = self.env.ref('account.invoice_tree')
        return {
            'name': u'销售发票',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('id', 'in', [self.sale_invoice_id.id])]
        }

    def open_purchase_invoice(self):
        self.ensure_one()
        return {
            'name': u'采购发票',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', [x.id for x in self.purchase_invoice_ids.filtered(lambda x: x.yjzy_type == 'purchase')])]
        }

    def open_back_tax_invoice(self):
        self.ensure_one()
        return {
            'name': '销售发票',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', [self.back_tax_invoice_id.id])]
        }

    def action_transport_bill_vendor_report(self):
        return self.env.ref('yjzy_extend.action_report_transport_bill_vendor').report_action(self.tb_vendor_ids)








