# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api,_
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning,UserError


class account_invoice(models.Model):
    _inherit = 'account.invoice'

    @api.depends('payment_term_id', 'date_due')
    def compute_date_deadline(self):
        strptime = datetime.strptime
        for one in self:
            if one.date_due and one.date_invoice and one.payment_term_id.invoice_date_deadline_field:
                dump_date = getattr(one, one.payment_term_id.invoice_date_deadline_field)
                if not dump_date:
                    continue
                diff = strptime(dump_date, DF) - strptime(one.date_invoice, DF)
                one.date_deadline = (strptime(one.date_due, DF) + diff).strftime(DF)
                one.date_deadline_new = (strptime(one.date_due, DF) + diff).strftime(DF)

    def compute_info(self):

        for one in self:
            one.purchase_date_finish_att_count = len(one.purchase_date_finish_att)

    @api.depends('date_deadline','date_ship','date_finish','date_invoice','date_out_in','date_due','date')
    def compute_times(self):
        today = datetime.today()
        strptime = datetime.strptime
        for one in self:
            if one.date_deadline:
               residual_times = today - strptime(one.date_deadline,DF)
               one.residual_times = residual_times.days
               one.residual_times_new = residual_times.days
            else:
                one.residual_times = -999
                one.residual_times_new = -999
            if one.date_due:
                residual_times_out_in = today - strptime(one.date_due, DF)#参考
                one.residual_times_out_in = residual_times_out_in.days
                one.residual_times_out_in_new = residual_times_out_in.days
            else:
                one.residual_times_out_in = -999
                one.residual_times_out_in_new = -999

    @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
                 'currency_id', 'company_id', 'date_invoice', 'type')
    def compute_amount(self):
        for one in self:
            one.amount_automatic = sum(line.price_total for line in one.invoice_line_ids_origin)
            one.amount_manual = sum(line.price_total for line in one.invoice_line_ids_add)

    @api.depends('residual_times','date_ship','date_finish')
    def compute_residual_date_group(self):
        residual_date_group = 'un_begin'
        for one in self:
            if one.date_deadline:
                if one.residual_times >= 60:
                    residual_date_group = 'after_60'
                if one.residual_times >= 30 and one.residual_times < 60:
                    residual_date_group = 'after_30'
                if one.residual_times >= 0 and one.residual_times < 30:
                    residual_date_group = '0_30'
                if one.residual_times >= -30 and one.residual_times < 0:
                    residual_date_group = 'before_30'
                if one.residual_times >= -60 and one.residual_times < -30:
                    residual_date_group = 'before_30_60'
                if one.residual_times >= -90 and one.residual_times < -60:
                    residual_date_group = 'before_60_90'
                if one.residual_times < -90:
                    residual_date_group = 'before_90'
            else:
                residual_date_group = 'un_begin'
            one.residual_date_group = residual_date_group
    def _get_reconcile_order_line_char(self):
        for one in self:
            dlrs = one.reconcile_order_line_id
            # dlrs_2203 = one.payment_move_line_lds.move_id.line_ids.filtered(lambda mov: mov.account_idcode == '2203')
            # dlrs_220301 = one.payment_move_line_lds.move_id.line_ids.filtered(lambda mov: mov.account_idcode == '220301')
            # dlrs_5603 = one.payment_move_line_lds.move_id.line_ids.filtered(lambda mov: mov.account_idcode == '5603')
            # dlrs_5601 = one.payment_move_line_lds.move_id.line_ids.filtered(lambda mov: mov.account_idcode == '5601')
            reconcile_order_line_char = ''
            reconcile_order_line_payment_char = ''
            reconcile_order_line_advance_char = ''
            reconcile_order_line_bank_char = ''
            reconcile_order_line_amount_diff_char = ''
            reconcile_order_line_so_id_char = ''
            # for o in dlrs:
            #     if o.amount_payment_org != 0:
            #         reconcile_order_line_payment_char +='%s: %s\n' % (o.order_id.date, o.amount_payment_org)
            #     if o.amount_advance_org != 0:
            #         reconcile_order_line_advance_char += '%s: %s\n' % (o.order_id.date, o.amount_advance_org)
            #     if o.amount_bank_org != 0:
            #         reconcile_order_line_bank_char += '%s: %s\n' % (o.order_id.date, o.amount_bank_org)
            #     if o.amount_diff_org != 0:
            #         reconcile_order_line_amount_diff_char += '%s: %s\n' % (o.order_id.date, o.amount_diff_org)
            for o in dlrs:
                reconcile_order_line_char += '%s\n' % (o.order_id.date)
                reconcile_order_line_payment_char +='%s\n' % (o.amount_payment_org)
                reconcile_order_line_advance_char += '%s\n' % (o.amount_advance_org)
                reconcile_order_line_bank_char += '%s\n' % ( o.amount_bank_org)
                reconcile_order_line_amount_diff_char += '%s\n' % ( o.amount_diff_org)
                reconcile_order_line_so_id_char += '%s\n' % ( o.so_id.contract_code)
            # for o in dlrs_2203:
            #     reconcile_order_line_char += '%s: %s\n' % (o.order_id.date)
            #     reconcile_order_line_advance_char += '%s\n' % (o.amount_advance_org)
            # for o in dlrs_220301:
            #     reconcile_order_line_char += '%s: %s\n' % (o.order_id.date)
            #     reconcile_order_line_payment_char +='%s\n' % (o.amount_payment_org)
            # for o in dlrs_5603:
            #     reconcile_order_line_char += '%s: %s\n' % (o.order_id.date)
            #     reconcile_order_line_bank_char += '%s\n' % ( o.amount_bank_org)
            # for o in dlrs_5601:
            #     reconcile_order_line_char += '%s: %s\n' % (o.order_id.date)
            #     reconcile_order_line_amount_diff_char += '%s\n' % ( o.amount_diff_org)
            one.reconcile_order_line_char = reconcile_order_line_char
            one.reconcile_order_line_so_id_char = reconcile_order_line_so_id_char
            one.reconcile_order_line_payment_char = reconcile_order_line_payment_char
            one.reconcile_order_line_advance_char = reconcile_order_line_advance_char
            one.reconcile_order_line_bank_char = reconcile_order_line_bank_char
            one.reconcile_order_line_amount_diff_char = reconcile_order_line_amount_diff_char

    @api.depends('reconcile_order_line_id','reconcile_order_line_id.amount_payment_org','reconcile_order_line_id.amount_advance_org','reconcile_order_line_id.amount_bank_org','reconcile_order_line_id.amount_diff_org','reconcile_order_line_id.yjzy_payment_id')
    def get_reconcile_order_line(self):
        for one in self:
            dlrs = one.reconcile_order_line_id
            # reconcile_order_line_payment = 0.0
            # reconcile_order_line_advance = 0.0
            # reconcile_order_line_bank = 0.0
            # reconcile_order_line_amount_diff = 0.0
            reconcile_order_line_payment = sum(x.amount_payment_org for x in dlrs) or 0.0
            reconcile_order_line_advance = sum(x.amount_advance_org for x in dlrs) or 0.0
            reconcile_order_line_bank = sum(x.amount_bank_org for x in dlrs) or 0.0
            reconcile_order_line_amount_diff = sum(x.amount_diff_org for x in dlrs) or 0.0
            one.reconcile_order_line_payment = reconcile_order_line_payment
            one.reconcile_order_line_advance = reconcile_order_line_advance
            one.reconcile_order_line_bank = reconcile_order_line_bank
            one.reconcile_order_line_amount_diff = reconcile_order_line_amount_diff


    @api.depends('tb_contract_code', 'amount_total')
    def compute_display_name(self):
        for one in self:
            one.display_name = '%s[%s]' % (one.tb_contract_code, str(one.amount_total))


    #新增
    display_name = fields.Char(u'显示名称', compute=compute_display_name, store=True)
   #13ok
    yjzy_type = fields.Selection([('sale', u'销售'), ('purchase', u'采购'), ('back_tax', u'退税')], string=u'发票类型')
    bill_id = fields.Many2one('transport.bill', u'发运单')
    tb_contract_code = fields.Char(u'出运合同号', related='bill_id.ref', readonly=True)
    include_tax = fields.Boolean(u'含税', related='bill_id.include_tax')
    date_ship = fields.Date(u'出运船日期')
    date_finish = fields.Date(u'交单日期')
    purchase_date_finish_att = fields.Many2many('ir.attachment', string='供应商交单日附件')
    purchase_date_finish_att_count = fields.Integer(u'供应商交单附件数量', compute=compute_info)
    purchase_date_finish_state = fields.Selection([('draft', u'待提交'), ('submit', u'待审批'), ('done', u'完成')], '供应商交单审批状态',
                                                  default='draft')
    date_deadline = fields.Date(u'到期日期', compute=compute_date_deadline)
    date_deadline_new = fields.Date(u'到期日期', compute=compute_date_deadline,store=True)#0723
    gongsi_id = fields.Many2one('gongsi', '内部公司')
    date_out_in = fields.Date('进仓日')
    #----
    reconcile_order_id = fields.Many2one('account.reconcile.order', u'核销单据')

    reconcile_order_line_id = fields.One2many('account.reconcile.order.line', 'invoice_id', u'核销明细行', domain=[('order_id.state','=','done'),('amount_total_org','!=',0)])
    reconcile_date = fields.Date(u'认领日期', related='reconcile_order_id.date')
    reconcile_order_line_char = fields.Text(compute=_get_reconcile_order_line_char, string=u'销售合同')
    reconcile_order_line_payment_char = fields.Text(compute=_get_reconcile_order_line_char, string=u'收款认领金额')
    reconcile_order_line_advance_char = fields.Text(compute=_get_reconcile_order_line_char, string=u'预收认领金额')
    reconcile_order_line_bank_char = fields.Text(compute=_get_reconcile_order_line_char, string=u'银行扣款认领金额')
    reconcile_order_line_amount_diff_char = fields.Text(compute=_get_reconcile_order_line_char, string=u'销售费用认领金额')
    reconcile_order_line_so_id_char = fields.Text(compute=_get_reconcile_order_line_char, string=u'销售合同')


    reconcile_order_line_payment = fields.Float(compute=get_reconcile_order_line, string=u'收款认领金额',store=True)
    reconcile_order_line_advance = fields.Float(compute=get_reconcile_order_line, string=u'预收认领金额',store=True)
    reconcile_order_line_bank = fields.Float(compute=get_reconcile_order_line, string=u'银行扣款认领金额',store=True)
    reconcile_order_line_amount_diff = fields.Float(compute=get_reconcile_order_line, string=u'销售费用认领金额',store=True)

    move_ids = fields.One2many('account.move', 'invoice_id', u'发票相关的分录', help=u'记录发票相关的分录，方便统计')
    move_line_ids = fields.One2many('account.move.line', 'invoice_id', u'发票相关的分录明细', help=u'记录发票相关的分录明细，方便统计')


    item_ids = fields.One2many('invoice.hs_name.item', 'invoice_id', u'品名汇总明细')
    po_id = fields.Many2one('purchase.order', u'采购订单')
    purchase_contract_code = fields.Char(u'合同编码', related='po_id.contract_code', readonly=True)

    sale_assistant_id = fields.Many2one('res.users', u'业务助理')

    #akiny
    tb_purchase_invoice_balance = fields.Monetary('对应应付余额',related='bill_id.purchase_invoice_balance_new' )
    tb_sale_invoice_balance = fields.Monetary('对应应收余额', related='bill_id.sale_invoice_balance_new')
    invoice_line_ids_add = fields.One2many('account.invoice.line','invoice_id', domain=[('is_manual', '=', True)],
                                           readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    invoice_line_ids_origin = fields.One2many('account.invoice.line', 'invoice_id', domain=[('is_manual', '=', False)],
                                           readonly=True, states={'draft': [('readonly', False)]}, copy=True)
    amount_automatic = fields.Monetary('原始合计金额',compute=compute_amount)
    amount_manual = fields.Monetary('手动合计金额',compute=compute_amount)
    residual_date_group = fields.Selection([('after_60',u'逾期>60天'),('after_30',u'逾期>30天'),('0_30',u'逾期0-30天'),
                                          ('before_30',u'未来30天'),('before_30_60',u'未来30-60天'),
                                          ('before_60_90',u'未来60-90天'),('before_90',u'未来超过90天'),('un_begin',u'未开始')],'到期时间组',store=True,
                                           compute=compute_residual_date_group)
    residual_times = fields.Integer('逾期天数',compute=compute_times)
    residual_times_new = fields.Integer('逾期天数', compute=compute_times, store=True)
    residual_times_out_in = fields.Integer('进仓日逾期天数', compute=compute_times)
    residual_times_out_in_new = fields.Integer('进仓日逾期天数', compute=compute_times, store=True)
    state = fields.Selection([
        ('draft', u'未确认'),
        ('open', u'已确认'),
        ('paid', u'已付款'),
        ('cancel', u'已取消'),
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used when the invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")

    def open_reconcile_order_line(self):
        self.ensure_one()
        #form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.account_yshxd_line_tree_view')
        for one in self:
            return {
                'name': u'客户应收',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.reconcile.order.line',
                'type': 'ir.actions.act_window',
                'views': [(tree_view.id, 'tree')],
                'domain': [('invoice_id', 'in', [one.id]),('order_id.state','=','done')],
                'target':'new'

            }
    def open_supplier_reconcile_order_line(self):
        self.ensure_one()
        #form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.account_yfhxd_line_tree_view')
        for one in self:
            return {
                'name': u'供应商应付',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.reconcile.order.line',
                'type': 'ir.actions.act_window',
                'views': [(tree_view.id, 'tree')],
                'domain': [('invoice_id', 'in', [one.id]),('order_id.state','=','done')],
                'target':'new'

            }

    # def name_get(self):
    #     ctx = self.env.context
    #     print('=111====', ctx)
    #
    #
    #     res = []
    #     for one in self:
    #         if ctx.get('params', {}).get('model', '') == 'transport.bill' and:
    #             name = '%s %s' % (one.partner_id.name or '',  one.date_finish or '')
    #         else:
    #             name = '暂无交单时间'
    #         res.append((one.id, name))
    #     return res
    @api.multi
    def name_get(self):
        show_date_finish = self.env.context.get('show_date_finish')
        print('=112====', show_date_finish)
        res = []

        for one in self:
            purchase_date_finish_state = one.purchase_date_finish_state
            if one.purchase_date_finish_state == 'draft':
                purchase_date_finish_state = '草稿'
            if one.purchase_date_finish_state == 'submit':
                purchase_date_finish_state = '待审批'
            if one.purchase_date_finish_state == 'done':
                purchase_date_finish_state = '完成'
            if show_date_finish:
                name = '%s %s %s' % (purchase_date_finish_state or '',one.date_finish or '', one.partner_id.name or '', )
            else:
                name=one.number
            res.append((one.id, name))
        print('=111====',res)
        return res

    # def name_get(self):
    #     # 多选：显示名称=（如果有客户编号显示客户编码，否则显示内部编码）+商品名称+关键属性，关键属性，供应商型号
    #     result = []
    #
    #     only_name = self.env.context.get('only_name')
    #     only_code = self.env.context.get('only_code')
    #
    #     # cat_name = self.env.context.get('cat_name')
    #     # print('==name_get==', only_name, self.env.context)
    #
    #     def _get_name(one):
    #         if only_name:
    #             name = one.name
    #         elif only_code:
    #             name = one.default_code
    #         # elif cat_name:
    #         #    name = '%s-%s-%s' % (one.categ_id.parent_id.name, one.categ_id.name, one.name)
    #         else:
    #             name = '[%s]%s{%s}' % (one.default_code, one.name, one.key_value_string)
    #
    #         ref = one.customer_ref or one.customer_ref2
    #         if ref:
    #             name = '(%s)%s' % (ref, name)
    #         return name
    #
    #     for one in self:
    #         result.append((one.id, _get_name(one)))
    #     return result







    def clear_zero_line(self):
        for one in self:
            for line in one.invoice_line_ids:
                if line.quantiy == 0:
                    line.unlink()


    def make_hs_name_items(self):
        self.ensure_one()
        self.item_ids.unlink()

        item_obj = self.env['invoice.hs_name.item']
        dic_hs_lines = {}
        for line in self.invoice_line_ids:
            hs_name = line.product_id.hs_name
            if hs_name not in dic_hs_lines:
                dic_hs_lines[hs_name] = line
            else:
                dic_hs_lines[hs_name] |= line

        for hs_name, lines in dic_hs_lines.items():
            item = item_obj.create({
                'invoice_id': self.id,
                'name': hs_name,
            })
            item.invoice_line_ids = lines
            item.compute_info()

    def action_purchase_date_finish_state_submit(self):
        for one in self:
            if not one.date_finish:
                raise Warning('请先填写日期')
            if not one.purchase_date_finish_att :
                raise Warning('请提交附件')
            one.purchase_date_finish_state = 'submit'




    def action_purchase_date_finish_state_done(self):
        for one in self:
            one.purchase_date_finish_state = 'done'
    def action_purchase_date_finish_state_refuse(self):
        for one in self:
            one.purchase_date_finish_state = 'refuse'

    def auto_account_invoice_open(self):
        today = datetime.today()
        strptime = datetime.strptime
        company_after_date_out_in_times =self.company_id.after_date_out_in_times
        for one in self:
            if one.date_out_in:
                after_date_out_in_times = today - strptime(one.date_out_in, DF)
                if after_date_out_in_times >= company_after_date_out_in_times and one.bill_id.sale_type != 'proxy':
                    one.action_invoice_open()


    @api.multi
    def action_invoice_cancel_1(self):
        if self.filtered(lambda inv: inv.state not in ['draft', 'open','paid']):
            raise UserError(_("Invoice must be in draft or open state in order to be cancelled."))
        return self.action_cancel()


class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    @api.depends('sale_line_ids')
    def _compute_so(self):
        for one in self:
            one.so_id = one.sale_line_ids and one.sale_line_ids[0].order_id or False

    item_id = fields.Many2one('invoice.hs_name.item', 'Item')

    so_id = fields.Many2one('sale.order', u'销售订单', compute=_compute_so)
    is_manual = fields.Boolean('是否手动添加', default=False)


class invoice_hs_name_item(models.Model):
    _name = 'invoice.hs_name.item'

    def compute_info(self):
        for one in self:
            one.product_id = one.invoice_line_ids.sorted(key=lambda x: x.quantity, reverse=True)[0].product_id
            one.qty = sum(one.invoice_line_ids.mapped('quantity'))
            one.amount = sum(one.invoice_line_ids.mapped('price_total'))
            one.price = one.amount / one.qty

    name = fields.Char('名称')
    invoice_id = fields.Many2one('account.invoice', u'发票')
    product_id = fields.Many2one('product.product', u'产品')
    qty = fields.Float(u'数量')
    price = fields.Float(u'价格')
    amount = fields.Float(u'金额', digits=dp.get_precision('Money'))
    invoice_line_ids = fields.One2many('account.invoice.line', 'item_id', 'Lines')
