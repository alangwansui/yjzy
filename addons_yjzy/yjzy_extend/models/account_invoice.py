# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning, UserError
from .comm import invoice_attribute_all_in_one

Invoice_Selection = [('draft', u'草稿'),
                     ('submit', u'已提交'),
                     ('approved', u'待总经理审批'),
                     ('done', u'执行中'),
                     ('invoice_pending', u'待处理账单'),
                     ('paid', u'付款完成'),
                     ('refuse', u'拒绝'),
                     ('cancel', u'取消'),
                     ('invoice_origin', u'原始账单')]


class AccountInvoiceStage(models.Model):
    _name = "account.invoice.stage"
    _description = "Invoice Stage"
    _order = 'sequence'

    name = fields.Char('Stage Name', translate=True, required=True)
    code = fields.Char('code')
    sequence = fields.Integer(help="Used to order the note stages", default=1)
    state = fields.Selection(Invoice_Selection, 'State',
                             default=Invoice_Selection[0][0])  # track_visibility='onchange',
    fold = fields.Boolean('Folded by Default')
    # _sql_constraints = [
    #     ('name_code', 'unique(code)', u"编码不能重复"),
    # ]
    user_ids = fields.Many2many('res.users', 'ref_invoice_users', 'fid', 'tid', 'Users')  # 可以进行判断也可以结合自定义视图模块使用
    group_ids = fields.Many2many('res.groups', 'ref_invoice_group', 'gid', 'bid', u'Groups')


class account_invoice(models.Model):
    _inherit = 'account.invoice'

    @api.depends('payment_term_id', 'payment_term_id.invoice_date_deadline_field','date_due','supplier_delivery_date', 'date_ship', 'date_finish', 'date_invoice')
    def compute_date_deadline(self):
        strptime = datetime.strptime
        for one in self:
            one._onchange_payment_term_date_invoice()
            if one.date_due and one.date_invoice and one.payment_term_id.invoice_date_deadline_field:
                dump_date = getattr(one, one.payment_term_id.invoice_date_deadline_field)
                print('dump_date_akiny', dump_date,one.payment_term_id.invoice_date_deadline_field)
                if not dump_date:
                    continue
                one._onchange_payment_term_date_invoice()
                diff = strptime(dump_date, DF) - strptime(one.date_invoice, DF)
                one.date_deadline = (strptime(one.date_due, DF) + diff).strftime(DF)
                one.date_deadline_new = (strptime(one.date_due, DF) + diff).strftime(DF)
            elif one.invoice_attribute in ['expense_po', 'other_payment']:
                one.date_deadline = one.date_due
                one.date_deadline_new = one.date_due
            else:
                one.date_deadline = one.date_due
                one.date_deadline_new = one.date_due

    def compute_info(self):
        for one in self:
            one.purchase_date_finish_att_count = len(one.purchase_date_finish_att)

    @api.depends('date_deadline', 'date_ship', 'date_finish', 'date_invoice', 'date_out_in', 'date_due', 'date',)
    def compute_times(self):
        today = datetime.today()
        strptime = datetime.strptime

        for one in self:
            one._onchange_payment_term_date_invoice()
            if one.state == 'open':
                if one.date_deadline:
                    residual_times = today -strptime(one.date_deadline, DF)
                    one.residual_times = residual_times.days
                    one.residual_times_new = residual_times.days
                else:
                    one.residual_times = -999
                    one.residual_times_new = -999
                if one.date_due:
                    residual_times_out_in = today - strptime(one.date_due, DF)    # 参考
                    one.residual_times_out_in = residual_times_out_in.days
                    one.residual_times_out_in_new = residual_times_out_in.days
                else:
                    one.residual_times_out_in = -999
                    one.residual_times_out_in_new = -999
            else:
                continue

    @api.depends('invoice_line_ids_origin.price_total', 'invoice_line_ids_add.price_total',
                 'currency_id', 'company_id', 'date_invoice', 'type')
    def compute_amount(self):
        for one in self:
            one.amount_automatic = sum(line.price_total for line in one.invoice_line_ids_origin)
            one.amount_manual = sum(line.price_total for line in one.invoice_line_ids_add)

    @api.depends('residual_times', 'date_ship', 'date_finish')
    def compute_residual_date_group(self):
        residual_date_group = 'un_begin'
        for one in self:
            if one.date_deadline:
                if one.residual_times >= 60:
                    residual_date_group = '10_after_60'
                if one.residual_times >= 30 and one.residual_times < 60:
                    residual_date_group = '20_after_30'
                if one.residual_times >= 0 and one.residual_times < 30:
                    residual_date_group = '30_0_30'
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
            dlrs = one.reconcile_order_line_approve_ids
            # dlrs_2203 = one.payment_move_line_lds.move_id.line_ids.filtered(lambda mov: mov.account_idcode == '2203')
            # dlrs_220301 = one.payment_move_line_lds.move_id.line_ids.filtered(lambda mov: mov.account_idcode == '220301')
            # dlrs_5603 = one.payment_move_line_lds.move_id.line_ids.filtered(lambda mov: mov.account_idcode == '5603')
            # dlrs_5601 = one.payment_move_line_lds.move_id.line_ids.filtered(lambda mov: mov.account_idcode == '5601')
            reconcile_order_line_char = ''
            # reconcile_order_line_approve_date_html = '<table width="90%" border="0" cellspacing="0" cellpadding="0" style="background-color: rgba(0,0,0,0.00)" ><tbody>'
            reconcile_order_line_approve_date_html = '<div style="width:80%">'
            reconcile_order_line_approve_date_char = ''
            reconcile_order_line_payment_char = ''
            # reconcile_order_line_payment_html = '<table width="70%" border="0" cellspacing="0" cellpadding="0" style="background-color: rgba(0,0,0,0.00)"><tbody>'
            reconcile_order_line_payment_html = '<div style="width:70%">'

            reconcile_order_line_advance_char = ''
            # reconcile_order_line_advance_html = '<table width="70%" border="0" cellspacing="0" cellpadding="0" style="background-color: rgba(0,0,0,0.00)"><tbody>'
            reconcile_order_line_advance_html = '<div style="width:70%">'

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
                if not o.approve_date:
                    approve_date = '&nbsp;'
                else:
                    approve_date = o.approve_date
                if not o.approve_date:
                    approve_date_1 = ' '
                else:
                    approve_date_1 = o.approve_date

                reconcile_order_line_char += '%s\n' % (o.order_id.date)
                # reconcile_order_line_approve_date_html += '%s%s%s%s%s' % ('<tr>', '<td style="background-color: rgba(0,0,0,0.00)">',approve_date,'</td>', '</tr>')
                reconcile_order_line_approve_date_html += '%s%s%s' % ('<div>', approve_date, '</div>')
                reconcile_order_line_approve_date_char += '%s\n' % (approve_date_1)
                reconcile_order_line_payment_char += '%s\n' % (o.amount_payment_org)
                # reconcile_order_line_payment_html += '%s%s%s%s%s' % ('<tr>', '<td style="text-align: right;background-color: rgba(0,0,0,0.00)">', o.amount_payment_org, '</td>', '</tr>')
                reconcile_order_line_payment_html += '%s%s%s' % ('<div>', o.amount_payment_org, '</div>')

                reconcile_order_line_advance_char += '%s\n' % (o.amount_advance_org)
                # reconcile_order_line_advance_html += '%s%s%s%s%s' % ('<tr>', '<td style="text-align: right;background-color: rgba(0,0,0,0.00)">', o.amount_advance_org, '</td>', '</tr>')
                reconcile_order_line_advance_html += '%s%s%s' % ('<div>', o.amount_advance_org, '</div>')

                reconcile_order_line_bank_char += '%s\n' % (o.amount_bank_org)
                reconcile_order_line_amount_diff_char += '%s\n' % (o.amount_diff_org)
                reconcile_order_line_so_id_char += '%s\n' % (o.so_id.contract_code)
                print('amount_payment_org', o.amount_payment_org)

            # reconcile_order_line_payment_html += '</tbody></table>'
            # reconcile_order_line_advance_html += '</tbody></table>'
            # reconcile_order_line_approve_date_html += '</tbody></table>'
            reconcile_order_line_payment_html += '</div>'
            reconcile_order_line_advance_html += '</div>'
            reconcile_order_line_approve_date_html += '</div>'

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
            one.reconcile_order_line_approve_date_char = reconcile_order_line_approve_date_char
            one.reconcile_order_line_approve_date_html = reconcile_order_line_approve_date_html
            one.reconcile_order_line_so_id_char = reconcile_order_line_so_id_char
            one.reconcile_order_line_payment_char = reconcile_order_line_payment_char
            one.reconcile_order_line_payment_html = reconcile_order_line_payment_html
            one.reconcile_order_line_advance_char = reconcile_order_line_advance_char
            one.reconcile_order_line_advance_html = reconcile_order_line_advance_html
            one.reconcile_order_line_bank_char = reconcile_order_line_bank_char
            one.reconcile_order_line_amount_diff_char = reconcile_order_line_amount_diff_char

    @api.depends('reconcile_order_line_id', 'reconcile_order_line_id.amount_payment_org',
                 'reconcile_order_line_id.order_id.state_1', 'reconcile_order_line_id.order_id.state',
                 'reconcile_order_line_id.amount_advance_org', 'reconcile_order_line_id.amount_bank_org',
                 'reconcile_order_line_id.amount_diff_org', 'reconcile_order_line_id.yjzy_payment_id')
    def get_reconcile_order_line(self):
        for one in self:
            dlrs = one.reconcile_order_line_id  # 原始账单的认领明细 已经完成的
            dlrs_payment_usd = one.reconcile_order_line_id.filtered(
                lambda x: x.payment_currency_id.name == 'USD')  # 原始账单收款美金
            dlrs_advance_usd = one.reconcile_order_line_id.filtered(
                lambda x: x.yjzy_payment_id.currency_id.name == 'USD')  # 原始账单预收美金 akiny注意：因为有些明细货币币种没有取过来，所以直接取预收单的货币

            dlrs_count = len(dlrs)
            yjzy_invoice_open_paid = one.yjzy_invoice_ids.filtered(lambda x: x.state in ['open', 'paid'])  # 额外账单

            # reconcile_order_line_payment = 0.0
            # reconcile_order_line_advance = 0.0
            # reconcile_order_line_bank = 0.0
            # reconcile_order_line_amount_diff = 0.0
            reconcile_order_line_payment = sum(x.amount_payment_org for x in dlrs) or 0.0  # 本账单收付款金额
            print('akiny_get_reconcile_order_line', dlrs, reconcile_order_line_payment)
            reconcile_order_line_advance = sum(x.amount_advance_org for x in dlrs) or 0.0  # 本账预收付认领金额
            reconcile_order_line_bank = sum(x.amount_bank_org for x in dlrs) or 0.0
            reconcile_order_line_amount_diff = sum(x.amount_diff_org for x in dlrs) or 0.0
            # 额外账单的收款明细以及预收明细，当yjzy_type='sale'的时候，当不是额外账单的时候才允许计算

            yjzy_reconcile_order_line_payment = sum(
                [x.reconcile_order_line_payment for x in yjzy_invoice_open_paid]) or 0.0  # 额外账单收付款金额
            yjzy_reconcile_order_line_advance = sum(
                [x.reconcile_order_line_advance for x in yjzy_invoice_open_paid]) or 0.0  # 额外账单预收付款认领金额
            all_amount_payment_org = yjzy_reconcile_order_line_payment + reconcile_order_line_payment  # 所有的收款金额
            all_amount_advance_org = yjzy_reconcile_order_line_advance + reconcile_order_line_advance  # 所有的预收金额
            all_amount_org = all_amount_advance_org + all_amount_payment_org  # 所有金额

            reconcile_order_line_payment_usd = sum(x.amount_payment_org for x in dlrs_payment_usd) or 0.0
            reconcile_order_line_advance_usd = sum(x.amount_advance_org for x in dlrs_advance_usd) or 0.0
            yjzy_reconcile_order_line_payment_usd = sum(
                [x.reconcile_order_line_payment_usd for x in yjzy_invoice_open_paid]) or 0.0
            yjzy_reconcile_order_line_advance_usd = sum(
                [x.reconcile_order_line_advance_usd for x in yjzy_invoice_open_paid]) or 0.0
            all_usd_amount_payment_org = reconcile_order_line_payment_usd + yjzy_reconcile_order_line_payment_usd
            all_usd_amount_advance_org = reconcile_order_line_advance_usd + yjzy_reconcile_order_line_advance_usd
            all_usd_amount_org = all_usd_amount_payment_org + all_usd_amount_advance_org

            one.reconcile_order_line_payment = reconcile_order_line_payment
            one.reconcile_order_line_advance = reconcile_order_line_advance
            one.reconcile_order_line_bank = reconcile_order_line_bank
            one.reconcile_order_line_amount_diff = reconcile_order_line_amount_diff

            one.yjzy_reconcile_order_line_payment = yjzy_reconcile_order_line_payment
            one.yjzy_reconcile_order_line_advance = yjzy_reconcile_order_line_advance
            one.all_amount_payment_org = all_amount_payment_org
            one.all_amount_advance_org = all_amount_advance_org
            one.all_amount_org = all_amount_org
            one.all_usd_amount_org = all_usd_amount_org
            one.all_usd_amount_payment_org = all_usd_amount_payment_org
            one.all_usd_amount_advance_org = all_usd_amount_advance_org
            one.reconcile_order_line_payment_usd = yjzy_reconcile_order_line_payment_usd
            one.reconcile_order_line_advance_usd = yjzy_reconcile_order_line_advance_usd
            one.reconcile_order_line_count = dlrs_count

    @api.depends('bill_id.ref', 'amount_total', 'bill_id.ref', 'date_finish')
    def compute_display_name(self):
        for one in self:
            show_date_finish = self.env.context.get('show_date_finish')
            supplier_delivery_date = self.env.context.get('supplier_delivery_date')
            # one.display_name = '%s[%s]' % (one.tb_contract_code, str(one.amount_total))
            # if show_date_finish:
            #     if one.date_finish:
            #         name = '%s %s' % (
            #             one.date_finish or '', one.partner_id.name or '',)
            #     else:
            #         name = '%s %s' % (
            #             '无交单日', one.partner_id.name or '',)
            if supplier_delivery_date:
                if one.supplier_delivery_date:
                    name = '%s %s' % (
                        one.supplier_delivery_date or '', one.partner_id.name or '',)
                else:
                    name = '%s %s' % (
                        '无发货日', one.partner_id.name or '',)
            else:
                if one.bill_id:
                    # else:
                    # if one.invoice_attribute_all_in_one == '220':
                    #     name = '%s:%s' % ('增加采购应付', one.tb_contract_code)
                    # elif one.invoice_attribute_all_in_one == '110':
                    #     name = '%s:%s' % ('主账单应付', one.tb_contract_code)
                    # elif one.invoice_attribute_all_in_one == '120':
                    #     name = '%s:%s' % ('主账单应收', one.tb_contract_code)
                    # elif one.invoice_attribute_all_in_one == '130':
                    #     name = '%s:%s' % ('主账单退税', one.tb_contract_code)
                    # elif one.invoice_attribute_all_in_one == '210':
                    #     name = '%s:%s' % ('增加采购应收', one.tb_contract_code)
                    # elif one.invoice_attribute_all_in_one == '230':
                    #     name = '%s:%s' % ('增加采购退税', one.tb_contract_code)
                    # elif one.invoice_attribute_all_in_one == '310':
                    #     name = '%s:%s' % ('费用转货款应收', one.tb_contract_code)
                    # elif one.invoice_attribute_all_in_one == '320':
                    #     name = '%s:%s' % ('费用转货款应付', one.tb_contract_code)
                    # elif one.invoice_attribute_all_in_one == '330':
                    #     name = '%s:%s' % ('费用转货款退税', one.tb_contract_code)
                    # elif one.invoice_attribute_all_in_one == '410':
                    #     name = '%s:%s' % ('其他应收', one.number)
                    # elif one.invoice_attribute_all_in_one == '510':
                    #     name = '%s:%s' % ('其他应付', one.number)

                    name = '%s' % (one.bill_id.ref)

                else:
                    name = '%s' % (one.number)

            one.display_name = name
            print('display_name', one.display_name)

    @api.model
    def _default_invoice_stage(self):
        stage = self.env['account.invoice.stage']
        return stage.search([('code', '=', '001')], limit=1)

    def _compute_count(self):
        for one in self:
            one.yjzy_invoice_count = len(one.yjzy_invoice_ids)

    # 额外账单只计算open和paid
    @api.depends('yjzy_invoice_ids', 'external_invoice_done', 'currency_id', 'yjzy_invoice_ids.amount_total_signed',
                 'yjzy_invoice_ids.amount_payment_can_approve_all', 'yjzy_invoice_ids.residual_signed', 'residual',
                 'amount_total', 'declare_amount_total')
    def compute_yjzy_invoice_amount_total(self):
        for one in self:
            # 计算额外账单应收总金额
            yjzy_invoice_amount_total = sum(
                one.yjzy_invoice_ids.filtered(lambda inv: inv.state in ['open', 'paid']).mapped('amount_total_signed'))
            print(yjzy_invoice_amount_total)
            # 计算额外账单未收总金额
            yjzy_invoice_residual_signed_total = sum(
                one.yjzy_invoice_ids.filtered(lambda inv: inv.state in ['open', 'paid']).mapped('residual_signed'))
            yjzy_invoice_amount_payment_can_approve_all = sum(
                one.yjzy_invoice_ids.filtered(lambda inv: inv.state in ['open', 'paid']).mapped(
                    'amount_payment_can_approve_all'))
            yjzy_total = one.amount_total_signed + yjzy_invoice_amount_total
            yjzy_residual = one.residual_signed + yjzy_invoice_residual_signed_total
            yjzy_paid = yjzy_total - yjzy_residual
            usd_pool = 0.0
            external_usd_pool = 0.0
            usd_pool_1 = 0.0
            usd_pool_2 = 0.0
            usd_pool_3 = 0.0
            usd_pool_4 = 0.0
            declare_amount_total = 0.0
            all_usd_amount_org = 0.0
            usd_pool_id = False
            payment_diff = 0.0
            # 美金发票，销售发票，原始发票，才开始计算美金池
            if one.currency_id.name == 'USD' and one.yjzy_type == 'sale' and one.is_yjzy_invoice == False:
                declare_amount_total = one.declare_amount_total
                all_usd_amount_org = one.all_usd_amount_org
                payment_diff = yjzy_total - all_usd_amount_org
                print('dddd', yjzy_total, yjzy_paid, yjzy_residual, payment_diff)
                if not one.bill_id:
                    usd_pool = all_usd_amount_org
                    usd_pool_4 = all_usd_amount_org
                    usd_pool_1 = 0.0
                    usd_pool_2 = 0.0
                    usd_pool_3 = 0.0
                    usd_pool_id = self.env.ref('yjzy_extend.usd_pool_state5').id
                else:
                    if yjzy_residual == 0:
                        if payment_diff > 100:
                            usd_pool_3 = all_usd_amount_org - declare_amount_total
                            usd_pool_1 = 0.0
                            usd_pool_2 = 0.0
                            usd_pool_4 = 0.0
                            usd_pool = all_usd_amount_org - declare_amount_total
                            usd_pool_id = self.env.ref('yjzy_extend.usd_pool_state3').id
                        else:
                            usd_pool_3 = yjzy_total - declare_amount_total
                            usd_pool = yjzy_total - declare_amount_total
                            usd_pool_1 = 0.0
                            usd_pool_2 = 0.0
                            usd_pool_4 = 0.0
                            usd_pool_id = self.env.ref('yjzy_extend.usd_pool_state4').id
                    else:
                        usd_pool = yjzy_total - declare_amount_total
                        usd_pool_2 = yjzy_total - declare_amount_total
                        usd_pool_1 = 0.0
                        usd_pool_3 = 0.0
                        usd_pool_4 = 0.0
                        usd_pool_id = self.env.ref('yjzy_extend.usd_pool_state2').id
                if one.external_invoice_done == '20_yes' or one.external_invoice_done == '30_not':
                    external_usd_pool = usd_pool
                else:
                    external_usd_pool = 0.0
            one.yjzy_invoice_amount_total = yjzy_invoice_amount_total
            one.yjzy_invoice_residual_signed_total = yjzy_invoice_residual_signed_total
            one.yjzy_total = yjzy_total
            one.yjzy_residual = yjzy_residual
            one.usd_pool = usd_pool
            one.usd_pool_1 = usd_pool_1
            one.usd_pool_2 = usd_pool_2
            one.usd_pool_3 = usd_pool_3
            one.usd_pool_4 = usd_pool_4
            one.payment_diff = payment_diff
            one.usd_pool_id = usd_pool_id
            one.external_usd_pool = external_usd_pool
            one.yjzy_invoice_amount_payment_can_approve_all = yjzy_invoice_amount_payment_can_approve_all

    def compute_yjzy_price_total(self):
        yjzy_price_total = 0.0
        for one in self:
            yjzy_price_total = sum(one.invoice_line_ids.mapped('yjzy_price_total'))
            one.yjzy_price_total = yjzy_price_total

    @api.depends('bill_id.ciq_amount', 'bill_id.hsname_ids.amount2')
    def compute_declare_amount_total(self):
        for one in self:
            if one.currency_id.name == 'USD':
                declare_amount_total = one.bill_id.ciq_amount
                one.declare_amount_total = declare_amount_total

    # def compute_usd_pool(self):
    #     for one in self:

    @api.depends('partner_id')
    def _compute_invoice_tb_partner_ids(self):
        for one in self:
            if one.bill_id:
                invoice_tb_partner_ids = self.env['account.invoice'].search(
                    [('partner_id', '=', one.partner_id.id), ('bill_id', '=', one.bill_id.id)])
                invoice_tb_partner_ids_1 = self.env['account.invoice'].search(
                    [('partner_id', '=', one.partner_id.id), ('bill_id', '=', one.bill_id.id), ('id', '!=', one.id)])
                one.invoice_tb_partner_ids = invoice_tb_partner_ids
                one.invoice_tb_partner_ids_1 = invoice_tb_partner_ids_1
            else:
                one.invoice_tb_partner_ids = False
                one.invoice_tb_partner_ids_1 = False
            print('one.invoice_tb_partner_ids', one.invoice_tb_partner_ids)

    def compute_reconcile_order_ids(self):
        for one in self:
            reconcile_order_ids = self.env['account.reconcile.order'].search([('invoice_ids', 'in', one.id)])
            print('reconcile_order_ids_akiny', reconcile_order_ids)
            reconcile_order_ids_count = len(reconcile_order_ids)
            one.reconcile_order_ids = reconcile_order_ids
            one.reconcile_order_ids_count = reconcile_order_ids_count

    def compute_tb_po_invoice_ids(self):
        for one in self:
            tb_po_invoice_ids_count = len(one.tb_po_invoice_ids)
            # tb_hsname_all_ids_count = len(one.tb_hsname_all_ids)
            one.tb_po_invoice_ids_count = tb_po_invoice_ids_count
            # one.tb_hsname_all_ids_count = tb_hsname_all_ids_count

    def compute_po_ids(self):
        for one in self:
            po_ids = one.invoice_line_ids.mapped('purchase_id')
            one.po_ids = po_ids

    def compute_so_ids(self):
        for one in self:
            so_ids = one.invoice_line_ids.mapped('so_id')
            one.so_ids = so_ids

    # 0921 = self.bill_id = self.partner
    #
    # invoice_tb_partner_ids = fields.Many2many('account.invoice',u'和出运相关的账单',compute=_compute_invoice_tb_partner_ids)
    # invoice_tb_partner_ids_1 = fields.Many2many('account.invoice', u'和出运相关的账单', compute=_compute_invoice_tb_partner_ids)
    @api.depends('amount_total', 'residual', 'reconcile_order_line_ids',
                 'reconcile_order_line_ids.amount_total_org_new', 'reconcile_order_line_ids.order_id.state',
                 'yjzy_invoice_reconcile_order_line_no_ids.amount_payment_org', 'reconcile_order_line_no_ids',
                 'reconcile_order_line_no_ids.order_id.state',
                 'reconcile_order_line_no_ids.amount_payment_org',
                 'yjzy_invoice_reconcile_order_line_no_ids', 'yjzy_invoice_reconcile_order_line_ids',
                 'yjzy_invoice_reconcile_order_line_no_ids.order_id.state')
    def compute_amount_payment_can_approve_all(self):
        for one in self:
            payment_approved_all = one.reconcile_order_line_ids.filtered(
                lambda x: x.order_id.state == 'approved')  # 完成审批
            payment_approved_no_all = one.reconcile_order_line_no_ids.filtered(lambda x: x.order_id.state == 'approved')

            payment_done_all = one.reconcile_order_line_ids.filtered(lambda x: x.order_id.state == 'done')  # 完成付款和认领
            payment_no_done_all = one.reconcile_order_line_no_ids.filtered(
                lambda x: x.order_id.state == 'done')  # 完成付款和认领

            payment_approval_all = one.reconcile_order_line_ids.filtered(
                lambda x: x.order_id.state == 'posted')  # 完成付款和认领
            payment_no_approval_all = one.reconcile_order_line_no_ids.filtered(
                lambda x: x.order_id.state == 'posted')  # 完成付款和认领

            payment_draft_all = one.reconcile_order_line_ids.filtered(
                lambda x: x.order_id.state == 'draft')  # 完成付款和认领
            payment_no_draft_all = one.reconcile_order_line_no_ids.filtered(
                lambda x: x.order_id.state == 'draft')  # 完成付款和认领

            yjzy_payment_approve_all = one.yjzy_invoice_reconcile_order_line_ids.filtered(
                lambda x: x.order_id.state == 'approved')
            yjzy_payment_approved_no_all = one.yjzy_invoice_reconcile_order_line_no_ids.filtered(
                lambda x: x.order_id.state == 'approved')

            amount_advance_org_done = sum(x.amount_advance_org for x in payment_done_all)
            amount_payment_org_done_old = sum(x.amount_payment_org for x in payment_done_all)
            amount_payment_org_done_new = sum(x.amount_payment_org for x in payment_no_done_all)
            amount_payment_org_done = amount_payment_org_done_new > 0 and amount_payment_org_done_new or amount_payment_org_done_new + amount_payment_org_done_old

            amount_advance_org_approval = sum(x.amount_advance_org for x in payment_approval_all)
            amount_payment_org_approval_old = sum(x.amount_payment_org for x in payment_approval_all)
            amount_payment_org_approval_new = sum(x.amount_payment_org for x in payment_no_approval_all)
            amount_payment_org_approval = amount_payment_org_approval_new > 0 and amount_payment_org_approval_new or amount_payment_org_approval_new + amount_payment_org_approval_old

            # sum(x.amount_payment_org for x in payment_no_approval_all)

            amount_advance_org_draft = sum(x.amount_advance_org for x in payment_draft_all)
            amount_payment_org_draft = sum(x.amount_payment_org for x in payment_no_draft_all)

            amount_advance_org_draft_approval = amount_advance_org_draft + amount_advance_org_approval
            amount_payment_org_draft_approval = amount_payment_org_draft + amount_payment_org_approval

            amount_payment_org_approved_old = sum(x.amount_payment_org for x in payment_approved_all)
            amount_payment_org_approved_new = sum(x.amount_payment_org for x in payment_approved_no_all)
            amount_payment_org_approved = amount_payment_org_approved_new > 0 and amount_payment_org_approved_new or amount_payment_org_approved_new + amount_payment_org_approved_old

            amount_payment_approve_all = sum(x.amount_total_org_new for x in payment_approved_all) + sum(
                x.amount_payment_org for x in payment_approved_no_all)

            yjzy_amount_payment_approve_all = sum(x.amount_total_org_new for x in yjzy_payment_approve_all) + sum(
                x.amount_payment_org for x in yjzy_payment_approved_no_all)
            amount_payment_can_approve_all = one.residual_signed - amount_payment_approve_all or 0.0  # 由amount_payment_org改为amount_total_org

            yjzy_amount_payment_can_approve_all = one.yjzy_residual - yjzy_amount_payment_approve_all or 0.0
            print('yjzy_amount_payment_can_approve_all', yjzy_amount_payment_can_approve_all,
                  amount_payment_can_approve_all)

            one.amount_advance_org_draft = amount_advance_org_draft
            one.amount_payment_org_draft = amount_payment_org_draft

            one.amount_advance_org_draft_approval = amount_advance_org_draft_approval
            one.amount_payment_org_draft_approval = amount_payment_org_draft_approval

            one.amount_advance_org_approval = amount_advance_org_approval
            one.amount_payment_org_approval = amount_payment_org_approval

            one.amount_payment_org_approved = amount_payment_org_approved
            one.amount_payment_org_done = amount_payment_org_done
            one.amount_advance_org_done = amount_advance_org_done
            one.amount_payment_approve_all = amount_payment_approve_all
            one.amount_payment_can_approve_all = amount_payment_can_approve_all
            one.yjzy_amount_payment_can_approve_all = yjzy_amount_payment_can_approve_all

    @api.depends('reconcile_order_line_no_ids', 'reconcile_order_line_no_ids.amount_payment_org',
                 'reconcile_order_line_ids', 'reconcile_order_line_ids.amount_advance_org',
                 'reconcile_order_line_ids.order_id.state',
                 'reconcile_order_line_ids.amount_payment_org', )
    def compute_amount_payment_approval_all(self):
        for one in self:
            amount_payment_payment_approval_all = one.reconcile_order_line_no_ids.filtered(
                lambda x: x.order_id.state == 'posted')  # 这个用来算应付
            amount_payment_advance_approval_all = one.reconcile_order_line_ids.filtered(
                lambda x: x.order_id.state == 'posted')  # 这个用来算预付

            amount_payment_approval_all = sum(x.amount_payment_org for x in amount_payment_payment_approval_all) + \
                                          sum(x.amount_advance_org for x in amount_payment_advance_approval_all)
            one.amount_payment_approval_all = amount_payment_approval_all

    @api.depends('state', 'residual')
    def compute_tb_po_invoice(self):
        for one in self:
            if one.tb_po_invoice_id:
                tb_po_invoice_back_tax_ids = self.env['account.invoice'].search(
                    [('tb_po_invoice_id', '=', one.tb_po_invoice_id.id), ('yjzy_type_1', '=', 'back_tax')])

                tb_po_invoice_p_s_ids = self.env['account.invoice'].search(
                    [('tb_po_invoice_id', '=', one.tb_po_invoice_id.id), ('yjzy_type_1', '=', 'purchase'),
                     ('type', '=', 'in_refund'), ])
                tb_po_invoice_s_ids = self.env['account.invoice'].search(
                    [('tb_po_invoice_id', '=', one.tb_po_invoice_id.id), ('yjzy_type_1', '=', 'sale'),
                     ('type', '=', 'out_invoice')])

                tb_po_invoice_all_ids = self.env['account.invoice'].search(
                    [('tb_po_invoice_id', '=', one.tb_po_invoice_id.id)])

                one.tb_po_invoice_back_tax_ids = tb_po_invoice_back_tax_ids
                one.tb_po_invoice_back_tax_ids_count = len(tb_po_invoice_back_tax_ids)

                one.tb_po_invoice_p_s_ids = tb_po_invoice_p_s_ids
                one.tb_po_invoice_p_s_ids_count = len(tb_po_invoice_p_s_ids)
                one.tb_po_invoice_s_ids = tb_po_invoice_s_ids
                one.tb_po_invoice_s_ids_count = len(tb_po_invoice_s_ids)

                one.tb_po_invoice_all_ids = tb_po_invoice_all_ids
                one.tb_po_invoice_all_ids_count = len(tb_po_invoice_all_ids)

    @api.depends('tb_po_invoice_back_tax_ids', 'tb_po_invoice_s_ids', 'tb_po_invoice_id', 'tb_po_invoice_id',
                 'tb_po_invoice_id.invoice_ids.amount_total_signed',
                 'tb_po_invoice_id.invoice_ids.residual_signed',
                 'tb_po_invoice_id.invoice_ids.amount_payment_can_approve_all')
    def compute_tb_invoice_amount(self):
        for one in self:
            tb_po_invoice_back_tax_ids = one.tb_po_invoice_back_tax_ids
            tb_po_invoice_back_tax_ids_amount_total = sum(x.amount_total_signed for x in tb_po_invoice_back_tax_ids)
            tb_po_invoice_back_tax_ids_residual = sum(x.residual_signed for x in tb_po_invoice_back_tax_ids)
            tb_po_invoice_back_tax_ids_can_approve_all = sum(
                x.amount_payment_can_approve_all for x in tb_po_invoice_back_tax_ids)

            tb_po_invoice_s_ids = one.tb_po_invoice_s_ids
            tb_po_invoice_s_ids_amount_total = sum(x.amount_total_signed for x in tb_po_invoice_s_ids)
            tb_po_invoice_s_ids_residual = sum(x.residual_signed for x in tb_po_invoice_s_ids)
            tb_po_invoice_s_ids_can_approve_all = sum(x.amount_payment_can_approve_all for x in tb_po_invoice_s_ids)

            one.tb_po_invoice_back_tax_ids_amount_total = tb_po_invoice_back_tax_ids_amount_total
            one.tb_po_invoice_back_tax_ids_residual = tb_po_invoice_back_tax_ids_residual
            one.tb_po_invoice_back_tax_ids_can_approve_all = tb_po_invoice_back_tax_ids_can_approve_all

            one.tb_po_invoice_s_ids_amount_total = tb_po_invoice_s_ids_amount_total
            one.tb_po_invoice_s_ids_residual = tb_po_invoice_s_ids_residual
            one.tb_po_invoice_s_ids_can_approve_all = tb_po_invoice_s_ids_can_approve_all

    @api.depends('tb_po_hsname_all_ids')
    def compute_tb_po_hsname_all_ids_count(self):
        for one in self:
            one.tb_po_hsname_all_ids_count = len(one.tb_po_hsname_all_ids)

    @api.depends('btd_line_ids', 'btd_line_ids.declaration_amount')
    def compute_declaration_amount(self):
        for one in self:
            one.declaration_amount = sum(x.declaration_amount for x in one.btd_line_ids)
            one.declaration_amount_latest = one.btd_line_ids and one.btd_line_ids[0].declaration_amount or 0

    # D
    @api.depends('yjzy_type_1', 'yjzy_type', 'invoice_attribute')
    def compute_all_in_one(self):
        for one in self:
            yjzy_type = one.yjzy_type_1 or one.yjzy_type
            print('yjzy_type_akiny', yjzy_type)
            invoice_attribute = one.invoice_attribute
            name = ''
            if invoice_attribute == 'normal':
                if yjzy_type == 'sale':
                    name = '110'
                elif yjzy_type == 'purchase':
                    name = '120'
                else:
                    name = '130'
            elif invoice_attribute == 'other_po':
                if yjzy_type == 'sale':
                    name = '210'
                elif yjzy_type == 'purchase':
                    name = '220'
                else:
                    name = '230'
            elif invoice_attribute == 'expense_po':
                if yjzy_type == 'sale':
                    name = '310'
                elif yjzy_type == 'purchase':
                    name = '320'
                else:
                    name = '330'
            elif invoice_attribute == 'other_payment':
                if yjzy_type == 'other_payment_sale':
                    name = '410'
                else:
                    name = '510'
            elif invoice_attribute == 'extra' and yjzy_type == 'back_tax':
                name = '640'

            one.invoice_attribute_all_in_one = name

    # D
    def compute_payment_log_ids_count(self):
        for one in self:
            one.payment_log_ids_count = len(one.payment_log_ids)
            one.payment_log_no_done_ids_count = len(one.payment_log_no_done_ids)
            one.payment_log_hexiao_ids_count = len(one.payment_log_hexiao_ids)

    @api.depends('tb_po_invoice_id', 'tb_po_invoice_id.is_yjzy_tb_po_invoice',
                 'tb_po_invoice_id.is_yjzy_tb_po_invoice_parent')
    def compute_yjzy_tb_po_child_patent(self):
        for one in self:
            one.is_yjzy_tb_po_invoice = one.tb_po_invoice_id.is_yjzy_tb_po_invoice
            one.is_yjzy_tb_po_invoice_parent = one.tb_po_invoice_id.is_yjzy_tb_po_invoice_parent

    def compute_move_com_count(self):
        for one in self:
            one.move_line_com_yfzk_ids_count = len(one.move_line_com_yfzk_ids)
            one.move_line_com_yszk_ids_count = len(one.move_line_com_yszk_ids)
            one.reconcile_order_line_no_ids_count = len(one.reconcile_order_line_no_ids)

    @api.depends('reconcile_order_id_advance_draft_ids', 'reconcile_order_id_payment_draft_ids')
    def compute_reconcile_order_id_draft_ids_count(self):
        for one in self:
            one.reconcile_order_id_advance_draft_ids_count = len(one.reconcile_order_id_advance_draft_ids)
            one.reconcile_order_id_payment_draft_ids_count = len(one.reconcile_order_id_payment_draft_ids)
            print('reconcile_order_id_advance_draft_ids_akiny')

    @api.depends('payment_log_hexiao_ids', 'reconcile_order_line_bank', 'reconcile_order_line_amount_diff',
                 'payment_log_hexiao_ids.state', 'payment_log_hexiao_ids.amount', 'reconcile_order_line_ids',
                 'reconcile_order_line_ids.order_id.state')
    def compute_payment_log_hexiao_amount(self):
        for one in self:
            payment_log_hexiao_ids = one.payment_log_hexiao_ids.filtered(lambda x: x.state in ['posted', 'reconciled'])
            payment_log_hexiao_amount = sum(x.amount for x in payment_log_hexiao_ids)

            reconcile_order_line_amount_diff = one.reconcile_order_line_amount_diff
            reconcile_order_line_bank = one.reconcile_order_line_bank

            one.payment_log_hexiao_amount = payment_log_hexiao_amount + reconcile_order_line_amount_diff + reconcile_order_line_bank

    def compute_days_term(self):
        for one in self:
            days_term = 0
            for x in one.payment_term_id.line_ids:
                if x.value == 'balance':
                    days_term = x.days
            one.days_term = days_term

    @api.depends('invoice_line_ids', 'invoice_line_ids.advice_advance_amount',
                 'invoice_line_ids.advice_advance_amount_1', 'amount_advance_org_done', 'amount_payment_can_approve_all',
                 'invoice_line_ids.rest_advance_so_po_balance')
    def compute_advance_pre_rest(self):
        for one in self:
            advance_pre = sum(x.advice_advance_amount for x in one.invoice_line_ids)

            rest_advance_so_po_balance = sum(x.rest_advance_so_po_balance for x in one.invoice_line_ids)
            jianyi_advance = sum(x.advice_advance_amount_1 for x in one.invoice_line_ids)

            amount_advance_org_done = one.amount_advance_org_done
            wait_advance = advance_pre - amount_advance_org_done
            amount_payment_can_approve_all_1 = one.amount_payment_can_approve_all - wait_advance
            one.advance_pre = advance_pre
            one.wait_advance = wait_advance >= 0 and wait_advance or 0
            one.amount_payment_can_approve_all_1 = amount_payment_can_approve_all_1
            one.rest_advance_so_po_balance = rest_advance_so_po_balance
            one.jianyi_advance = jianyi_advance < rest_advance_so_po_balance and jianyi_advance or rest_advance_so_po_balance



    @api.depends('tb_po_invoice_id', 'tb_po_invoice_id.invoice_ids', 'tb_po_invoice_id.invoice_ids.amount_total',
                 'tb_po_invoice_id.invoice_ids.residual')
    def compute_in_invoice_amount(self):
        for one in self:
            in_invoice_id = one.tb_po_invoice_all_ids.filtered(lambda x: x.yjzy_type_1 == 'purchase')
            print('in_invoice_id_akiny', in_invoice_id)
            if in_invoice_id:
                in_invoice_amount = in_invoice_id[0].amount_total
                in_invoice_residual = in_invoice_id[0].residual
                one.in_invoice_amount = in_invoice_amount
                one.in_invoice_residual = in_invoice_residual

    def _default_tenyale_name(self):
        invoice_tenyale_name = self.env.context.get('default_invoice_tenyale_name')
        if invoice_tenyale_name:
            tenyale_name = self.env['ir.sequence'].next_by_code('account.invoice.%s' % invoice_tenyale_name)
        else:
            tenyale_name = self.env['ir.sequence'].next_by_code('account.invoice.tenyale_invoice')
        return tenyale_name

    @api.depends('btd_line_ids', 'btd_line_ids.btd_id')
    def compute_df_new_id(self):
        for one in self:
            df_new_id = one.btd_line_ids.mapped('btd_id')
            if len(df_new_id) == 1:
                one.df_new_id = df_new_id
            else:
                one.df_new_id = False

    @api.depends('supplier_delivery_date')
    def compute_po_delivered_date(self):
        for one in self:
            one.po_delivered_date = one.supplier_delivery_date

    is_editable = fields.Boolean(u'可编辑')
    purchase_invoice_hsname_ids = fields.One2many('purchase.invoice.hsname', 'invoice_id', '采购发票明细')
    tenyale_name = fields.Char(u'天宇编号', default=lambda self: self._default_tenyale_name())
    is_manual = fields.Boolean('是否手动创建', default=False)

    # @api.depends('invoice_line_ids', 'amount_advance_org_done','amount_payment_can_approve_all')
    def compute_advance_pre_rest_new(self):
        for one in self:
            po_ids = one.invoice_line_ids.mapped('purchase_id')
            advance_before_delivery_pre = 0
            advice_advance =0
            rest_advance_so_po_balance = 0
            real_advance_new = 0 #采购实际预付金额
            pre_advance_advance = 0
            pre_advance_before_delivery = 0
            for po in po_ids:
                advance_before_delivery_pre += po.real_advance_before_delivery_new#发货前的预付
                real_advance_new += po.real_advance_new #实际预付金额（不含发货前）

                pre_advance_advance += po.pre_advance_advance#预计
                pre_advance_before_delivery += po.pre_advance_before_delivery#预计发货前

                invoice_line_po_ids = one.invoice_line_ids.filtered(lambda x: x.purchase_id == po) #这个采购合同的发货明细
                delivery_amount_po = sum(x.price_total for x in invoice_line_po_ids)#算出这个采购合同 的发货金额

                po_amount = po.amount_total #采购合同总金额
                delivery_po_percent = po_amount !=0 and delivery_amount_po / po_amount or 0 #发货和出运比例
                advice_advance += po.real_advance_new * delivery_po_percent #建议预付认领金额

                rest_advance_so_po_balance += po.balance_new


            wait_advance = advice_advance + advance_before_delivery_pre
            amount_payment_can_approve_all_1 = one.amount_payment_can_approve_all - wait_advance
            one.advance_before_delivery_pre = advance_before_delivery_pre#实际建议发货前预付认领金额
            one.wait_advance_new = wait_advance >= 0 and wait_advance or 0 # 建议预付认领总金额
            one.amount_payment_can_approve_all_1_new = amount_payment_can_approve_all_1#可申请支付金额
            one.rest_advance_so_po_balance_new = rest_advance_so_po_balance #总剩余未认领预付金额
            one.advice_advance_new = advice_advance < rest_advance_so_po_balance and advice_advance or rest_advance_so_po_balance

    # @api.depends('invoice_line_ids', 'price_total', 'so_id', 'so_id.amount_total', 'so_id.real_advance',
    #              'so_id.balance_new', 'invoice_id', 'invoice_id.type')
    # def compute_original_so_po_amount(self):
    #     for one in self:
    #         if one.invoice_id.type == 'in_invoice':
    #             po_ids = one.invoice_line_ids.mapped('purchase_id')
    #             rest_advance_so_po_balance = 0
    #             real_advance = 0
    #             original_so_po_amount = 0
    #             for po in po_ids:
    #                 rest_advance_so_po_balance += po.balance_new
    #                 real_advance += po.real_advance
    #                 original_so_po_amount += po.amount_total
    #             proportion_tb = original_so_po_amount != 0 and one.price_total / original_so_po_amount or 0
    #             advice_advance_amount = proportion_tb * real_advance
    #             advice_advance_amount_1 = proportion_tb * rest_advance_so_po_balance
    #             one.original_so_po_amount = original_so_po_amount
    #             one.rest_advance_so_po_balance = rest_advance_so_po_balance
    #             one.proportion_tb = proportion_tb
    #             one.advice_advance_amount = advice_advance_amount
    #             one.advice_advance_amount_1 = advice_advance_amount_1
    #
    #         if one.invoice_id.type == 'out_invoice':
    #             original_so_po_amount = one.so_id.amount_total
    #             real_advance = one.so_id.real_advance
    #             rest_advance_so_po_balance = one.so_id.balance_new
    #             proportion_tb = original_so_po_amount != 0 and one.price_total / original_so_po_amount or 0
    #             advice_advance_amount = proportion_tb * real_advance
    #             advice_advance_amount_1 = proportion_tb * rest_advance_so_po_balance
    #
    #             one.original_so_po_amount = original_so_po_amount
    #             one.rest_advance_so_po_balance = rest_advance_so_po_balance
    #             one.proportion_tb = proportion_tb
    #             one.advice_advance_amount = advice_advance_amount
    #             one.advice_advance_amount_1 = advice_advance_amount_1

    advance_pre = fields.Monetary('建议认领预收付总金额', currency_field='currency_id', compute=compute_advance_pre_rest,
                                  store=True)


    wait_advance = fields.Monetary('待认领预付', currency_field='currency_id', compute=compute_advance_pre_rest,
                                   store=True)  # 相关剩余预收付金额
    amount_payment_can_approve_all_1 = fields.Monetary(u'减去建议待认领预付金额后可申请应收付款', currency_field='currency_id',
                                                       compute=compute_advance_pre_rest, store=True)
    rest_advance_so_po_balance = fields.Monetary('相关剩余预收预付款', currency_field='currency_id',
                                                 compute=compute_advance_pre_rest, store=True)
    jianyi_advance = fields.Monetary('建议预收预付', currency_field='currency_id',
                                     compute=compute_advance_pre_rest, store=True)  # 按照比例计算的预收付建议认领金额

    advance_pre_new = fields.Monetary('建议认领预收付总金额', currency_field='currency_id', compute=compute_advance_pre_rest,
                                  )
    advance_before_delivery_pre = fields.Monetary('建议发货前认领金额', currency_field='currency_id',
                                                  compute=compute_advance_pre_rest_new,
                                                  )

    wait_advance_new = fields.Monetary('待认领预付', currency_field='currency_id', compute=compute_advance_pre_rest_new,
                                   )  # 相关剩余预收付金额
    amount_payment_can_approve_all_1_new = fields.Monetary(u'减去建议待认领预付金额后可申请应收付款', currency_field='currency_id',
                                                       compute=compute_advance_pre_rest_new)
    rest_advance_so_po_balance_new = fields.Monetary('相关剩余预收预付款', currency_field='currency_id',
                                                 compute=compute_advance_pre_rest_new, )
    advice_advance_new = fields.Monetary('建议预收预付', currency_field='currency_id',
                                     compute=compute_advance_pre_rest_new,)  # 按照比例计算的预收付建议认领金额

    days_term = fields.Integer('账期', compute=compute_days_term)
    invoice_date_deadline = fields.Selection('账期计算方式', related='payment_term_id.invoice_date_deadline_field')

    invoice_attribute_all_in_one = fields.Selection(invoice_attribute_all_in_one, u'账单属性all_in_one',
                                                    compute=compute_all_in_one, store=True)

    current_date_rate = fields.Float('出运单汇率', related='bill_id.current_date_rate')
    # 讨论：是否在提交审批的时候就生成呢？日志就可以把核销和认领统一起来。
    payment_log_ids = fields.One2many('account.payment', 'invoice_log_id', '认领以及收付明细')
    payment_log_ids_count = fields.Integer('认领以及收付明细数量', compute=compute_payment_log_ids_count)
    payment_log_no_done_ids = fields.One2many('account.payment', 'invoice_log_id', '未完成认领以及收付明细',
                                              domain=[('state', 'not in', ['posted', 'reconciled'])])
    payment_log_no_done_ids_count = fields.Integer('未完成认领以及收付明细数量', compute=compute_payment_log_ids_count)
    payment_log_hexiao_ids = fields.One2many('account.payment', 'invoice_log_id', '核销单',
                                             domain=[('sfk_type', 'in', ['reconcile_yingshou', 'reconcile_yingfu'])])
    payment_log_hexiao_ids_count = fields.Integer('未完成认领以及收付明细数量', compute=compute_payment_log_ids_count)
    payment_log_hexiao_amount = fields.Monetary('核销金额', currency_field='currency_id',
                                                compute=compute_payment_log_hexiao_amount, store=True)

    other_payment_invoice_id = fields.Many2one('account.invoice', '关联的其他应收付下级账单')  # 目前 只对其他应收做了计算  #C
    other_payment_invoice_parent_id = fields.Many2one('account.invoice', '关联的其他应收付上级账单')  # C

    # 1029#通过他们是否同属于一张申请单来汇总所有相关账单,其他应收付和相关的应收付申请，这里还没有直接的联系，待处理
    back_tax_declaration_state = fields.Selection([('10', '未申报'), ('15', '部分申报'), ('20', '已申报')], '退税申报状态',
                                                  default='10')
    declaration_amount = fields.Monetary('申报总金额', currency_field='currency_id', compute=compute_declaration_amount,
                                         store=True)
    declaration_amount_latest = fields.Monetary('最新一次申报金额', currency_field='currency_id',
                                                compute=compute_declaration_amount,
                                                store=True)
    btd_line_ids = fields.One2many('back.tax.declaration.line', 'invoice_id', u'申报明细')

    tb_po_invoice_back_tax_ids = fields.Many2many('account.invoice', '相关退税账单', compute=compute_tb_po_invoice)  # C
    tb_po_invoice_back_tax_ids_count = fields.Integer('相关退税账单数量', compute=compute_tb_po_invoice)  # C
    tb_po_invoice_back_tax_ids_amount_total = fields.Monetary('相关退税账单金额', compute=compute_tb_invoice_amount,
                                                              store=True)  # C
    tb_po_invoice_back_tax_ids_residual = fields.Monetary('相关退税账单金额', compute=compute_tb_invoice_amount,
                                                          store=True)  # C
    tb_po_invoice_back_tax_ids_can_approve_all = fields.Monetary('相关退税账单金额', compute=compute_tb_invoice_amount,
                                                                 store=True)  # C

    tb_po_invoice_p_s_ids = fields.Many2many('account.invoice', '相关冲减账单', compute=compute_tb_po_invoice)  # C
    tb_po_invoice_p_s_ids_count = fields.Integer('相关冲减账单数量', compute=compute_tb_po_invoice)  # C
    tb_po_invoice_s_ids = fields.Many2many('account.invoice', '相关应收账单', compute=compute_tb_po_invoice)  # C
    tb_po_invoice_s_ids_count = fields.Integer('相关应收账单数量', compute=compute_tb_po_invoice)  # C
    tb_po_invoice_s_ids_amount_total = fields.Monetary('相关应收账单金额', compute=compute_tb_invoice_amount, store=True)  # C
    tb_po_invoice_s_ids_residual = fields.Monetary('相关应收账单金额', compute=compute_tb_invoice_amount, store=True)  # C
    tb_po_invoice_s_ids_can_approve_all = fields.Monetary('相关应收账单金额', compute=compute_tb_invoice_amount,
                                                          store=True)  # C

    tb_po_invoice_all_ids = fields.Many2many('account.invoice', '相关账单', compute=compute_tb_po_invoice)  # C
    tb_po_invoice_all_ids_count = fields.Integer('相关账单数量', compute=compute_tb_po_invoice)  # C

    name_title = fields.Char(u'账单描述')
    invoice_partner = fields.Char(u'账单对象')

    # 928
    bank_id = fields.Many2one('res.partner.bank', u'银行账号')
    fk_journal_id = fields.Many2one('account.journal', u'日记账', domain=[('type', 'in', ['cash', 'bank'])])
    # 作用，待处理
    tb_po_invoice_ids = fields.One2many('tb.po.invoice', 'yjzy_invoice_id', u'额外账单申请单', domain=[('type', '=', 'extra')])
    tb_po_invoice_ids_count = fields.Integer(u'额外账单申请单数量', compute=compute_tb_po_invoice_ids)
    # 0911

    yjzy_advance_payment_id = fields.Many2one('account.payment', u'预收付单')  # C 未定
    # 831增加对应报关申报表
    df_id = fields.Many2one('back.tax.declaration', u'报关申报表')

    df_new_id = fields.Many2one('back.tax.declaration', u'报关申报表', compute='compute_df_new_id', store=True)
    # 820增加一个和新增采购关联的字段，把退税等一起关联起来
    tb_po_invoice_id = fields.Many2one('tb.po.invoice', u'综合增加采购单', ondelete='cascade')  # C

    in_invoice_amount = fields.Monetary('增加采购应付金额', currency_field='currency_id', compute=compute_in_invoice_amount,
                                        store=True)
    in_invoice_residual = fields.Monetary('增加采购剩余应付', currency_field='currency_id', compute=compute_in_invoice_amount,
                                          store=True)

    tb_po_invoice_child_id = fields.Many2one('tb.po.invoice', related='tb_po_invoice_id.yjzy_tb_po_invoice')  # C
    is_yjzy_tb_po_invoice = fields.Boolean('是否有对应下级账单', compute=compute_yjzy_tb_po_child_patent, store=True)  # C
    tb_po_invoice_parent_id = fields.Many2one('tb.po.invoice',
                                              related='tb_po_invoice_id.yjzy_tb_po_invoice_parent')  # C
    is_yjzy_tb_po_invoice_parent = fields.Boolean('是否有对应上级账单', compute=compute_yjzy_tb_po_child_patent, store=True)  # C
    # 819费用转应付发票
    expense_sheet_id = fields.Many2one('hr.expense.sheet', u'费用报告')
    # 增加常规转直接的状态，明细那边增加是否已经转换的状态

    # 以下三个组成对账单的属性全局判断，主账单同时拥有yjzy_type和yjzy_type_1的两个值，以完成对老数据的过滤，新版本可以将两者合并
    invoice_attribute = fields.Selection(
        [('normal', u'主账单'),
         ('reconcile', u'核销账单'),  # 这个等待删除
         ('extra', u'额外账单'),  # 这个等待删除
         ('other_po', u'直接增加'),
         ('expense_po', u'费用转换'),
         ('other_payment', u'其他'),
         ], u'账单属性')

    yjzy_type_1 = fields.Selection([('sale', u'应收'),
                                    ('purchase', u'应付'),
                                    ('back_tax', u'退税'),
                                    ('other_payment_sale', '其他应收'),
                                    ('other_payment_purchase', '其他应付')  # 这个等待删除
                                    ], string=u'发票类型')

    invoice_type_main = fields.Selection([('10_main', u'常规账单'),
                                          ('20_extra', u'额外账单'),
                                          ('30_reconcile', u'核销账单')], u'账单类型')
    back_tax_type = fields.Selection([('normal', u'正常退税'),
                                      ('adjustment', u'调节退税'),
                                      ], string=u'退税类型', default='normal')

    # from_type = fields.Selection([('manual_create',u'手动创建'),('auto_crate',u'自动创建')],u'创建方式')

    need_refund = fields.Boolean(u'是否需要退款')  # C
    refund_state = fields.Selection([('10_no', '未退款'), ('20_part', '部分退款'), ('30_all', '完成退款')], u'退款状态')  # C

    hsname_all_ids = fields.One2many('invoice.hs_name.all', 'invoice_id',
                                     u'报关明细')  # 这个字段要增加，要和出运的tbl.hsmane.all保持一致，也就是申请单的一组
    # 显示开票资料对应出运单的报关资料汇总
    # tb_hsname_all_ids = fields.One2many('tbl.hsname.all', u'报关明细',related="bill_id.hsname_all_ids")
    tb_po_hsname_all_ids = fields.One2many('tb.po.invoice.line', u'开票(报关)明细',
                                           related="tb_po_invoice_id.hsname_all_ids")  # C
    tb_po_hsname_all_ids_count = fields.Integer('开票(报关)明细数量', compute=compute_tb_po_hsname_all_ids_count)  # C

    # tb_hsname_all_ids_count = fields.Integer('报关明细数量',compute=compute_tb_po_invoice_ids)
    external_invoice_done = fields.Selection([('10_no', u'否'),
                                              ('20_yes', u'是'),
                                              ('30_not', u'非')], '外账是否确认销售', default='10_no')

    external_usd_pool = fields.Float('外账美金池', compute=compute_yjzy_invoice_amount_total, store=True)
    usd_pool_id = fields.Many2one('usd.pool', u'美金池状态', compute=compute_yjzy_invoice_amount_total, store=True)
    hsname_ids = fields.One2many('tbl.hsname', u'HS统计', related='bill_id.hsname_ids')
    declare_amount_total = fields.Float(u'报关金额', compute=compute_declare_amount_total, store=True)
    all_amount_payment_org = fields.Float(u'所有账单收款认领金额', compute=get_reconcile_order_line, store=True)
    all_usd_amount_payment_org = fields.Float(u'所有账单美金收款认领金额', compute=get_reconcile_order_line, store=True)
    all_amount_advance_org = fields.Float(u'所有账单预收认领金额', compute=get_reconcile_order_line, store=True)
    all_usd_amount_advance_org = fields.Float(u'所有账单美金预收认领金额', compute=get_reconcile_order_line, store=True)
    all_amount_org = fields.Float(u'所有账单实际收款认领金额', compute=get_reconcile_order_line, store=True)
    all_usd_amount_org = fields.Float(u'所有账单实际美金收款认领金额', compute=get_reconcile_order_line, store=True)
    reconcile_order_line_payment_usd = fields.Float(compute=get_reconcile_order_line, string=u'美金收款认领金额', store=True)
    reconcile_order_line_advance_usd = fields.Float(compute=get_reconcile_order_line, string=u'美金预收认领金额', store=True)
    payment_diff = fields.Float('收款差额属性', compute=compute_yjzy_invoice_amount_total, store=True)
    usd_pool = fields.Float('美金池', compute=compute_yjzy_invoice_amount_total, store=True)
    usd_pool_1 = fields.Float('美金池1', compute=compute_yjzy_invoice_amount_total, store=True)
    usd_pool_2 = fields.Float('美金池2', compute=compute_yjzy_invoice_amount_total, store=True)
    usd_pool_3 = fields.Float('美金池3', compute=compute_yjzy_invoice_amount_total, store=True)
    usd_pool_4 = fields.Float('美金池4', compute=compute_yjzy_invoice_amount_total, store=True)
    stage_id = fields.Many2one(
        'account.invoice.stage',
        default=_default_invoice_stage, copy=False)

    state_1 = fields.Selection(Invoice_Selection, '账单审批', default='draft', index=True, related='stage_id.state', store=True,
                               track_visibility='onchange')
    # 新建一个账单的状态，可以用来筛选还没有开始付款申请的账单
    state_2 = fields.Selection([
        ('10_draft', u'未确认'),
        ('20_open', u'已确认未完成认领'),
        ('30_no_account_payment', u'已申请未付款'),
        ('35_no_account_payment', u'已申请未收款'),
        ('40_paid', u'已付款'),
        ('45_paid', u'已收款'),
        ('50_certified', u'已认证'),
        ('90_cancel', u'已取消'),
    ], string='Status', index=True, readonly=True, default='10_draft', copy=False, )

    # real_invoice_line_id = fields.Many2one('real.invoice.line',u'实际发票')
    # real_invoice_id = fields.Many2one('real.invoice',u'实际发票认证单')
    certifying = fields.Boolean('正在认证')

    fault_comments = fields.Text('异常备注')
    display_name = fields.Char(u'显示名称', compute=compute_display_name)
    # 13ok
    yjzy_type = fields.Selection([('sale', u'应收'), ('purchase', u'应付'), ('back_tax', u'退税')], string=u'发票类型')
    bill_id = fields.Many2one('transport.bill', u'发运单')
    tb_contract_code = fields.Char(u'出运合同号', related='bill_id.ref', readonly=True, store=True)
    include_tax = fields.Boolean(u'含税')
    supplier_delivery_date = fields.Date(u'供应商发货日期')
    date_ship = fields.Date(u'出运船日期')
    date_finish = fields.Date(u'交单日期')
    date_out_in = fields.Date('进仓日')

    po_delivered_date = fields.Date('供应商发货日期',compute="compute_po_delivered_date",store=True)
    purchase_date_finish_att = fields.Many2many('ir.attachment', string='供应商交单日附件')
    purchase_date_finish_att_count = fields.Integer(u'供应商交单附件数量', compute=compute_info)
    purchase_date_finish_state = fields.Selection([('draft', u'待提交'), ('submit', u'待审批'), ('done', u'完成')], '供应商交单审批状态',
                                                  default='draft')
    is_purchase_invoice_finish = fields.Boolean('供应商是否交单')
    date_deadline = fields.Date(u'到期日期', compute=compute_date_deadline)
    date_deadline_new = fields.Date(u'到期日期', compute=compute_date_deadline, store=True)  # 0723
    gongsi_id = fields.Many2one('gongsi', '内部公司')

    # ----
    reconcile_order_id = fields.Many2one('account.reconcile.order', u'核销单据')
    # 上面这个是M2o,现在改成M2M
    reconcile_order_ids = fields.Many2many('account.reconcile.order', 're_tb', 'te_td', u'核销单据',
                                           compute=compute_reconcile_order_ids)
    reconcile_order_ids_count = fields.Integer(u'核销单据数量', compute=compute_reconcile_order_ids)
    # hexiao_total = fields.Monetary(u'核销认领金额', currency_field='currency_id',
    #                                  compute=hexiao_renling_total,store=True)

    reconcile_order_id_ids = fields.One2many('account.reconcile.order', 'back_tax_invoice_id', '额外退税对应核销单')

    reconcile_order_id_advance_draft_ids = fields.One2many('account.reconcile.order', 'invoice_id', '草稿核销单预付',
                                                           domain=[('state', 'in', ['draft']),
                                                                   ('hxd_type_new', '=', '30')])
    reconcile_order_id_advance_draft_ids_count = fields.Integer('草稿核销单预付数量',
                                                                compute=compute_reconcile_order_id_draft_ids_count)
    reconcile_order_id_payment_draft_ids = fields.One2many('account.reconcile.order', 'invoice_id', '草稿核销单付款',
                                                           domain=[('state', 'in', ['draft']),
                                                                   ('hxd_type_new', '=', '40')])
    reconcile_order_id_payment_draft_ids_count = fields.Integer('草稿核销单付款数量',
                                                                compute=compute_reconcile_order_id_draft_ids_count)
    reconcile_order_line_id = fields.One2many('account.reconcile.order.line', 'invoice_id', u'核销明细行',
                                              domain=[('order_id.state', '=', 'done'), ('amount_total_org', '!=', 0)])

    reconcile_order_line_count = fields.Float(u'核销明细行数量', compute=get_reconcile_order_line)
    reconcile_order_line_ids = fields.One2many('account.reconcile.order.line', 'invoice_id', u'核销明细行',
                                               domain=[('order_id', '!=', False)]
                                               )  # , ('order_id.sfk_type', '=', 'yfhxd') domain=[('order_id.state', 'in', ['approved']), ('amount_total_org', '!=', 0)]
    reconcile_order_line_approve_ids = fields.One2many('account.reconcile.order.line', 'invoice_id', u'核销明细行',
                                                       domain=[('order_id.state', '=', 'approved'),
                                                               ('order_id', '!=', False),
                                                               ('order_id.sfk_type', '=', 'yfhxd')]
                                                       )  # domain=[('order_id.state', 'in', ['approved']), ('amount_total_org', '!=', 0)]
    reconcile_order_line_no_ids = fields.One2many('account.reconcile.order.line.no', 'invoice_id',
                                                  u'所有核销细行no', domain=[('order_id', '!=', False),
                                                                       ])  # ('order_id.sfk_type', '=', 'yfhxd')

    reconcile_order_line_no_ids_count = fields.Integer('no明细行数量', compute=compute_move_com_count)

    yjzy_invoice_reconcile_order_line_ids = fields.One2many('account.reconcile.order.line', 'yjzy_invoice_id',
                                                            u'所有核销明细行',
                                                            domain=[('order_id', '!=', False), (
                                                                'order_id.sfk_type', '=',
                                                                'yfhxd')])  # domain=[('order_id.state', 'in', ['approved']), ('amount_total_org', '!=', 0)]关联账单（额外账单以及自己）的所有认领明细
    yjzy_invoice_reconcile_order_line_no_ids = fields.One2many('account.reconcile.order.line.no', 'yjzy_invoice_id',
                                                               u'所有核销细行no', domain=[('order_id', '!=', False),
                                                                                    ('order_id.sfk_type', '=', 'yfhxd')]
                                                               )  # domain=[('order_id.state', 'in', ['approved']), ('amount_total_org', '!=', 0)]关联账单（额外账
    amount_payment_can_approve_all = fields.Monetary(u'可申请应收付款', currency_field='currency_id',
                                                     compute=compute_amount_payment_can_approve_all, store=True)

    amount_advance_org_done = fields.Monetary(u'预收付认领金额', currency_field='currency_id',
                                              compute=compute_amount_payment_can_approve_all, store=True)

    amount_payment_org_done = fields.Monetary(u'收付款金额', currency_field='currency_id',
                                              compute=compute_amount_payment_can_approve_all, store=True)

    amount_advance_org_approval = fields.Monetary(u'预收付未审批认领金额', currency_field='currency_id',
                                                  compute=compute_amount_payment_can_approve_all, store=True)

    amount_payment_org_approval = fields.Monetary(u'收付款未审批金额', currency_field='currency_id',
                                                  compute=compute_amount_payment_can_approve_all, store=True)

    amount_advance_org_draft_approval = fields.Monetary(u'预收付审批中_草稿认领金额', currency_field='currency_id',
                                                        compute=compute_amount_payment_can_approve_all, store=True)

    amount_payment_org_draft_approval = fields.Monetary(u'收付款审批中_草稿金额', currency_field='currency_id',
                                                        compute=compute_amount_payment_can_approve_all, store=True)

    amount_advance_org_draft = fields.Monetary(u'预收付草稿认领金额', currency_field='currency_id',
                                               compute=compute_amount_payment_can_approve_all, store=True)

    amount_payment_org_draft = fields.Monetary(u'收付款审草稿金额', currency_field='currency_id',
                                               compute=compute_amount_payment_can_approve_all, store=True)

    amount_payment_org_approved = fields.Monetary(u'已完成审批收付款金额', currency_field='currency_id',
                                                  compute=compute_amount_payment_can_approve_all, store=True)

    amount_payment_approval_all = fields.Monetary(u'审批中应收付款', currency_field='currency_id',
                                                  compute=compute_amount_payment_approval_all,
                                                  store=True)  # 未付金额-审批完成的付款金额

    amount_payment_approve_all = fields.Monetary(u'已审批未支付', currency_field='currency_id',
                                                 compute=compute_amount_payment_can_approve_all, store=True)
    yjzy_amount_payment_can_approve_all = fields.Monetary(u'所有可申请应收付款', currency_field='currency_id',
                                                          compute=compute_amount_payment_can_approve_all,
                                                          store=True)  # 包括额外账单的
    reconcile_date = fields.Date(u'认领日期', related='reconcile_order_id.date')
    reconcile_order_line_char = fields.Text(compute=_get_reconcile_order_line_char, string=u'销售合同')

    reconcile_order_line_approve_date_html = fields.Html(compute=_get_reconcile_order_line_char, string=u'确认日期')

    reconcile_order_line_approve_date_char = fields.Text(compute=_get_reconcile_order_line_char, string=u'确认日期')
    reconcile_order_line_payment_char = fields.Text(compute=_get_reconcile_order_line_char, string=u'收款认领金额')
    reconcile_order_line_payment_html = fields.Html(compute=_get_reconcile_order_line_char, string=u'收款认领金额')
    reconcile_order_line_advance_char = fields.Text(compute=_get_reconcile_order_line_char, string=u'预收认领金额')
    reconcile_order_line_advance_html = fields.Html(compute=_get_reconcile_order_line_char, string=u'预收认领金额')
    reconcile_order_line_bank_char = fields.Text(compute=_get_reconcile_order_line_char, string=u'银行扣款认领金额')
    reconcile_order_line_amount_diff_char = fields.Text(compute=_get_reconcile_order_line_char, string=u'销售费用认领金额')
    reconcile_order_line_so_id_char = fields.Text(compute=_get_reconcile_order_line_char, string=u'销售合同')

    reconcile_order_line_payment = fields.Monetary(compute=get_reconcile_order_line, currency_field='currency_id',
                                                   string=u'收款认领金额', store=True)
    yjzy_reconcile_order_line_payment = fields.Monetary(compute=get_reconcile_order_line, currency_field='currency_id',
                                                        string=u'收款认领金额', store=True)
    reconcile_order_line_advance = fields.Monetary(compute=get_reconcile_order_line, currency_field='currency_id',
                                                   string=u'预收认领金额', store=True)
    yjzy_reconcile_order_line_advance = fields.Monetary(compute=get_reconcile_order_line, currency_field='currency_id',
                                                        string=u'预收认领金额', store=True)
    reconcile_order_line_bank = fields.Monetary(compute=get_reconcile_order_line, currency_field='currency_id',
                                                string=u'银行扣款认领金额', store=True)
    reconcile_order_line_amount_diff = fields.Monetary(compute=get_reconcile_order_line, currency_field='currency_id',
                                                       string=u'销售费用认领金额', store=True)

    move_ids = fields.One2many('account.move', 'invoice_id', u'发票相关的分录', help=u'记录发票相关的分录，方便统计')
    move_line_ids = fields.One2many('account.move.line', 'invoice_id', u'发票相关的分录明细', help=u'记录发票相关的分录明细，方便统计')
    move_line_plan_ids = fields.One2many('account.move.line', 'plan_invoice_id', u'发票相关的分录明细', help=u'记录发票相关的分录明细，方便统计')
    move_line_yfzk_ids = fields.One2many('account.move.line', 'invoice_id', u'发票相关应付账款分录',
                                         domain=[('account_id.code', '=', '2202')])
    move_line_yszk_ids = fields.One2many('account.move.line', 'invoice_id', u'发票相关应收账款分录',
                                         domain=[('account_id.code', '=', '1122')])

    move_line_com_yfzk_ids = fields.One2many('account.move.line.com', 'invoice_id', u'应付日志',
                                             domain=[('account_id.code', '=', '2202')])
    move_line_com_yfzk_ids_count = fields.Integer('应付日志数量', compute=compute_move_com_count)
    move_line_com_yszk_ids = fields.One2many('account.move.line.com', 'invoice_id', u'应收日志',
                                             domain=[('account_id.code', '=', '1122')])
    move_line_com_yszk_ids_count = fields.Integer('应收日志数量', compute=compute_move_com_count)

    item_ids = fields.One2many('invoice.hs_name.item', 'invoice_id', u'品名汇总明细')
    po_id = fields.Many2one('purchase.order', u'采购订单')
    po_ids = fields.Many2many('purchase.order', 'invoice_po_ids_ref', 'po_id', 'invoice_id', compute=compute_po_ids)
    purchase_contract_code = fields.Char(u'合同编码', related='po_id.contract_code', readonly=True)
    so_ids = fields.Many2many('sale.order', 'invoice_so_ids_ref', 'so_id', 'invoice_id', compute=compute_so_ids)

    sale_assistant_id = fields.Many2one('res.users', u'业务助理')

    # akiny
    tb_purchase_invoice_balance = fields.Monetary('对应应付余额', related='bill_id.purchase_invoice_balance_new')
    tb_sale_invoice_balance = fields.Monetary('对应应收余额', related='bill_id.sale_invoice_balance_new')
    invoice_line_ids_add = fields.One2many('account.invoice.line', 'invoice_id', domain=[('is_manual', '=', True)],
                                           copy=True)
    invoice_line_ids_origin = fields.One2many('account.invoice.line', 'invoice_id',
                                              domain=[('quantity', '!=', 0)],
                                              readonly=True, states={'draft': [('readonly', False)]},
                                              copy=True)  # 本来是除去手动的 ，现在把手动的也加回去('is_manual', '=', False),
    amount_automatic = fields.Monetary('原始合计金额', currency_field='currency_id', compute=compute_amount)
    amount_manual = fields.Monetary('手动合计金额', currency_field='currency_id', compute=compute_amount)
    residual_date_group = fields.Selection(
        [('10_after_60', u'逾期>60天'), ('20_after_30', u'逾期>30天'), ('30_0_30', u'逾期0-30天'),
         ('before_30', u'未来30天'), ('before_30_60', u'未来30-60天'),
         ('before_60_90', u'未来60-90天'), ('before_90', u'未来超过90天'), ('un_begin', u'未开始')], '到期时间组', store=True,
        compute=compute_residual_date_group)
    residual_times = fields.Integer('逾期天数2', compute=compute_times)  # 发票日期计算
    residual_times_new = fields.Integer('逾期天数2', compute=compute_times, group_operator=False, store=True)
    residual_times_out_in = fields.Integer('逾期天数1', compute=compute_times)  # 进仓日计算
    residual_times_out_in_new = fields.Integer('逾期天数1', compute=compute_times, group_operator=False, store=True)
    state = fields.Selection([
        ('draft', u'未确认'),
        ('open', u'执行中'),
        ('paid', u'已结束'),
        ('cancel', u'已取消'),
    ], string='Status', index=True, readonly=True, default='draft',
        track_visibility='onchange', copy=False,
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Invoice.\n"
             " * The 'Pro-forma' status is used when the invoice does not have an invoice number.\n"
             " * The 'Open' status is used when user creates invoice, an invoice number is generated. It stays in the open status till the user pays the invoice.\n"
             " * The 'Paid' status is set automatically when the invoice is paid. Its related journal entries may or may not be reconciled.\n"
             " * The 'Cancelled' status is used when user cancel invoice.")
    yjzy_invoice_id = fields.Many2one('account.invoice', u'关联账单', default=lambda self: self.id)
    yjzy_invoice_back_tax_id = fields.Many2one('account.invoice', u'关联退税账单')  # 计算退税的增加减少和原来的退税的关系
    yjzy_invoice_count = fields.Integer(u'关联账单数量', compute=_compute_count)
    yjzy_invoice_ids = fields.One2many('account.invoice', 'yjzy_invoice_id', u'额外账单',
                                       domain=[('is_yjzy_invoice', '=', True)])
    yjzy_invoice_wait_payment_ids = fields.One2many('account.invoice', 'yjzy_invoice_id', u'额外账单',
                                                    domain=[('is_yjzy_invoice', '=', True),
                                                            ('type', 'in', ['out_invoice', 'in_invoice']),
                                                            ('state', 'in', ['open']),
                                                            ('amount_payment_can_approve_all', '!=', 0)])
    yjzy_invoice_all_ids = fields.One2many('account.invoice', 'yjzy_invoice_id', u'所有关联账单')  # 所有额外账单和原始账单
    yjzy_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms_1')
    yjzy_currency_id = fields.Many2one('res.currency', string='currency 1')  # 原来额外账单直接创建的时候需要用他来onchange，现在不需要
    is_yjzy_invoice = fields.Boolean(u'是否额外账单', default=False)
    yjzy_invoice_amount_total = fields.Monetary('额外账单应收金额', currency_field='currency_id',
                                                compute=compute_yjzy_invoice_amount_total, store=True)
    yjzy_invoice_residual_signed_total = fields.Monetary('额外账单未收金额', currency_field='currency_id',
                                                         compute=compute_yjzy_invoice_amount_total, store=True)
    yjzy_invoice_amount_payment_can_approve_all = fields.Monetary('额外账单可申请支付金额', currency_field='currency_id',
                                                                  compute=compute_yjzy_invoice_amount_total, store=True)
    yjzy_total = fields.Monetary(u'总应收金额', currency_field='currency_id', compute=compute_yjzy_invoice_amount_total,
                                 store=True)
    yjzy_residual = fields.Monetary(u'总未收金额', currency_field='currency_id', compute=compute_yjzy_invoice_amount_total,
                                    store=True)
    yjzy_price_total = fields.Monetary('新金额', currency_field='currency_id', compute=compute_yjzy_price_total)
    extra_code = fields.Char(u'额外编号', default=lambda self: self._default_name())
    yjzy_invoice_line_ids = fields.One2many('account.invoice.line', 'yjzy_invoice_id', u'所有明细',
                                            domain=[('quantity', '!=', 0),
                                                    ('invoice_attribute', 'in', ['normal', 'extra'])])

    plan_invoice_auto_id = fields.Many2one('plan.invoice.auto', '应收发票')
    plan_invoice_auto_state_1 = fields.Selection(
        [('10', '报关数据待锁定'), ('20', '报关数据已锁定-应收发票待锁定'), ('30', '应收发票锁定-发票未收齐'), ('40', '发票已收齐-未开销项'),
         ('50', '已开销项-未申报退税'), ('60', '已申报退税未收退税'), ('70', '已收退税')], related='plan_invoice_auto_id.state_1',
        string='state_1', store=True)
    back_tax_plan_invoice_auto_state_1 = fields.Selection(
        [('10', '报关数据待锁定'), ('20', '报关数据已锁定-应收发票待锁定'), ('30', '应收发票锁定-发票未收齐'), ('40', '发票已收齐-未开销项'),
         ('50', '已开销项-未申报退税'), ('60', '已申报退税未收退税'), ('70', '已收退税')],
        string='state_1', )
    plan_invoice_auto_state_2 = fields.Selection(
        [('10', '正常待锁定.'), ('20', '异常待锁定.'), ('30', '正常待锁定'), ('40', '异常待锁定'), ('50', '正常未收齐'),
         ('60', '异常未收齐'), ('70', '正常未开'), ('75', '异常未开'), ('80', '正常未申报'), ('90', '异常未申报'), ('100', '正常未收'),
         ('110', '异常未收'), ('120', '已收退税')], related='plan_invoice_auto_id.state_2', string='State', store=True)

    # 方案二0809

    # real_invoice_auto_ids = fields.Many2many('real.invoice.auto','实际发票')

    def _make_plan_invoice_auto(self):
        if self.type == 'in_invoice':
            pia_obj = self.env['plan.invoice.auto']
            # real_invoice_auto_id = self.env['real.invoice.auto'].search([('partner_id','=',self.partner_id.id),('bill_id','=',self.bill_id.id)],limit=1)
            plan_invoice_auto = pia_obj.create({
                'invoice_id': self.id,
                'bill_id': self.bill_id.id,
                # 'real_invoice_auto_id':real_invoice_auto_id.id
            })
            self.plan_invoice_auto_id = plan_invoice_auto
            plan_invoice_auto.compute_hs_name_all_ids()

    def make_plan_invoice_auto(self):
        if self.type == 'in_invoice':
            pia_obj = self.env['plan.invoice.auto']
            plan_invoice_auto_id = pia_obj.search([('bill_id', '=', self.bill_id.id)])
            if self.include_tax:
                if not plan_invoice_auto_id:
                    plan_invoice_auto = pia_obj.create({

                        'bill_id': self.bill_id.id,
                        # 'real_invoice_auto_id':real_invoice_auto_id.id
                    })
                    self.plan_invoice_auto_id = plan_invoice_auto
                    plan_invoice_auto.compute_hs_name_all_ids()
                else:
                    self.plan_invoice_auto_id = plan_invoice_auto_id
                    self.plan_invoice_auto_id.compute_hs_name_all_ids()

    def create_tenyale_name(self):
        for one in self:
            if one.invoice_attribute_all_in_one == '230':
                tenyale_name = self.env['ir.sequence'].next_by_code('account.invoice.%s' % 'ad_po')
            elif one.invoice_attribute_all_in_one == '330':
                tenyale_name = self.env['ir.sequence'].next_by_code('account.invoice.%s' % 'fx_po')
            else:
                tenyale_name = self.env['ir.sequence'].next_by_code('account.invoice.%s' % 'tenyale_invoice')
            one.tenyale_name = tenyale_name

    def compute_move_lines(self):
        for one in self.move_line_yfzk_ids:
            one.compute_sslj_balance()
        for one in self.move_line_yszk_ids:
            one.compute_sslj_balance()

    # 创建认证明细
    def create_real_invoice_line(self):
        real_invoice_id = self.env.context.get('real_invoice_id')
        certification_invoice_obj = self.env['sys.invoice.line']
        # 取得正在认证的实际发票明细行
        real_invoice_line_id = self.env['real.invoice.line'].search(
            [('real_invoice_id', '=', real_invoice_id), ('certifying', '=', True)], limit=1)

        sys_invoice_line = certification_invoice_obj.create({'real_invoice_id': real_invoice_id,
                                                             'invoice_id': self.id,
                                                             'amount': self.amount_total,
                                                             'real_invoice_line_id': real_invoice_line_id.id})
        # sys_invoice_line.real_invoice_line_id = real_invoice_line_id
        self.certifying = True
        return True

    # 913新建额外账单申请单
    def open_tb_po_invoice(self):
        form_view_supplier_id = self.env.ref('yjzy_extend.tb_po_form').id
        form_view_customer_id = self.env.ref('yjzy_extend.tb_po_extra_invoice_customer_form').id
        back_tax_invoice_id = self.bill_id.back_tax_invoice_id
        if self.is_yjzy_invoice:
            raise Warning('额外账单不允许创建额外账单申请！')
        if self.state != 'open':
            raise Warning('当前状态不允许创建额外账单申请')
        if self.yjzy_type == 'sale':
            return {
                'name': u'创建应收额外账单',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'tb.po.invoice',
                'type': 'ir.actions.act_window',
                'views': [(form_view_customer_id, 'form')],
                'target': 'current',
                'context': {'default_type': 'extra',
                            'default_tb_id': self.bill_id.id,
                            'default_yjzy_type_1': 'sale',
                            'default_yjzy_invoice_id': self.id,
                            'default_yjzy_invoice_back_tax_id': back_tax_invoice_id.id,
                            'default_partner_id': self.partner_id.id,
                            'default_is_tb_hs_id': True,
                            }
            }
        elif self.yjzy_type == 'purchase':
            return {
                'name': u'创建应付额外账单',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'tb.po.invoice',
                'type': 'ir.actions.act_window',
                'views': [(form_view_supplier_id, 'form')],
                'target': 'current',
                'context': {'default_type': 'extra',
                            'default_tb_id': self.bill_id.id,
                            'default_yjzy_type_1': 'purchase',
                            'default_partner_id': self.partner_id.id,
                            'default_yjzy_invoice_id': self.id,
                            'default_yjzy_invoice_back_tax_id': back_tax_invoice_id.id,
                            'default_is_tb_hs_id': True,
                            }
            }

    # 创建核销额外账单
    def open_tb_po_reconcile_invoice(self):
        form_view_supplier_id = self.env.ref('yjzy_extend.tb_po_extra_invoice_supplier_form').id
        form_view_customer_id = self.env.ref('yjzy_extend.tb_po_extra_invoice_customer_form').id
        if self.is_yjzy_invoice:
            raise Warning('额外账单不允许创建额外账单！')
        if self.state != 'open':
            raise Warning('当前状态不允许创建额外账单申请')
        if self.yjzy_type == 'sale':
            return {
                'name': u'创建核销应收额外账单',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'tb.po.invoice',
                'type': 'ir.actions.act_window',
                'views': [(form_view_customer_id, 'form')],
                'target': 'current',
                'context': {'default_type': 'reconcile',
                            'default_yjzy_type_1': 'sale',
                            'default_yjzy_invoice_id': self.id,
                            'default_partner_id': self.partner_id.id}
            }
        elif self.yjzy_type == 'purchase':
            return {
                'name': u'创建核销应付额外账单',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'tb.po.invoice',
                'type': 'ir.actions.act_window',
                'views': [(form_view_supplier_id, 'form')],
                'target': 'current',
                'context': {'default_type': 'reconcile',
                            'default_yjzy_type_1': 'purchase',
                            'default_partner_id': self.partner_id.id,
                            'default_yjzy_invoice_id': self.id, }
            }

    # 创建的时候，默认yjzy_invoice_id等于本身 928
    # @api.model
    # def create(self, vals):
    #     one = super(account_invoice, self).create(vals)
    #     # budget = self.env['budget.budget'].create({
    #     #     'type': 'transport',
    #     #     'tb_id': one.id,
    #     # })
    #     one.yjzy_invoice_id = one.id
    #     return one
    # 818
    def unlink(self):
        for one in self:
            one.hsname_all_ids.unlink()
        return super(account_invoice, self).unlink()

    # 更新原始账单的时候同时更新额外账单的时间
    def update_date(self):
        if self.yjzy_invoice_ids:
            for one in self.yjzy_invoice_ids:
                one.date_out_in = one.yjzy_invoice_id.date_out_in
                one.date_finish = one.yjzy_invoice_id.date_finish
                one.date_ship = one.yjzy_invoice_id.date_ship
                one.date = one.yjzy_invoice_id.date
                one.date_invoice = one.yjzy_invoice_id.date_invoice

    def _default_name(self):
        is_yjzy_invoice = self.env.context.get('is_yjzy_invoice')
        yjzy_invoice_number = self.env.context.get('yjzy_invoice_number')
        print('is_yjzy_invoice', is_yjzy_invoice, )
        if is_yjzy_invoice:
            name_1 = self.env['ir.sequence'].next_by_code('account.invoice.extra')
            name = '%s/%s' % (yjzy_invoice_number, name_1)
        else:
            name = yjzy_invoice_number
        return name

    def compute_name_extra(self):
        is_yjzy_invoice = self.is_yjzy_invoice
        yjzy_invoice_number = self.yjzy_invoice_id.number
        print('is_yjzy_invoice', is_yjzy_invoice, )
        if is_yjzy_invoice:
            name_1 = self.env['ir.sequence'].next_by_code('account.invoice.extra')
            name = '%s/%s' % (yjzy_invoice_number, name_1)
        else:
            name = yjzy_invoice_number
        self.extra_code = name

    # 费用转换为应付后，创建核销单并直接生成付款单。
    def create_yfhxd(self):
        # self.ensure_one()
        sfk_type = 'yfhxd'
        domain = [('code', '=', 'yfdrl'), ('company_id', '=', self.env.user.company_id.id)]
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        journal = self.env['account.journal'].search(domain, limit=1)
        account_obj = self.env['account.account']
        bank_account = account_obj.search(
            [('code', '=', '112301'), ('company_id', '=', self.env.user.company_id.id)],
            limit=1)
        yfhxd = self.env['account.reconcile.order'].create({
            'partner_id': self.partner_id.id,
            'manual_payment_currency_id': self.currency_id.id,
            'invoice_ids': [(4, self.id)],
            'payment_type': 'outbound',
            'fk_journal_id': self.fk_journal_id.id,
            'bank_id': self.bank_id.id,
            'partner_type': 'supplier',
            'sfk_type': 'yfhxd',
            'be_renling': True,
            'name': name,
            'journal_id': journal.id,
            'expense_sheet_id': self.expense_sheet_id.id,  # 1009
            'payment_account_id': bank_account.id,
            'invoice_attribute': self.invoice_attribute,
            'operation_wizard': '10',
            'hxd_type_new': '40',

        })
        self.reconcile_order_id = yfhxd
        # yfhxd._make_lines_po_from_expense()
        yfhxd.make_line_no()
        yfhxd.action_manager_approve_stage()
        # yfhxd.create_rcfkd()

        form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new')
        return {
            'name': u'应付核销单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.reconcile.order',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': self.reconcile_order_id.id,
            'target': 'current',
            'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }

    # #创建应付核销
    # def create_hexiao_yfhx(self):
    #     # self.ensure_one()
    #     sfk_type = 'yfhxd'
    #     domain = [('code', '=', 'yfdrl'), ('company_id', '=', self.env.user.company_id.id)]
    #     name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
    #     journal = self.env['account.journal'].search(domain, limit=1)
    #     account_obj = self.env['account.account']
    #     bank_account = account_obj.search(
    #         [('code', '=', '112301'), ('company_id', '=', self.env.user.company_id.id)],
    #         limit=1)
    #     yfhxd = self.env['account.reconcile.order'].create({
    #         'partner_id': self.partner_id.id,
    #         'manual_payment_currency_id': self.currency_id.id,
    #         'invoice_ids': [(4, self.id)],
    #         'payment_type': 'outbound',
    #         'fk_journal_id':self.fk_journal_id.id,
    #         'bank_id':self.bank_id.id,
    #         'partner_type': 'supplier',
    #         'sfk_type': 'yfhxd',
    #         'be_renling': True,
    #         'name': name,
    #         'journal_id': journal.id,
    #         'payment_account_id': bank_account.id,
    #         'invoice_attribute':self.invoice_attribute,
    #         'operation_wizard':'10',
    #         'hxd_type_new':'60',
    #     })
    #     line_no_obj = self.env['account.reconcile.order.line.no']
    #     self.line_no_ids = None
    #     for one in self.invoice_ids:
    #         amount_payment_org = one.residual
    #         so_ids = one.invoice_line_ids.mapped('so_id')
    #         po_ids = one.invoice_line_ids.mapped('purchase_id')
    #         advance_residual2 = sum(x.balance for x in so_ids)
    #         advance_residual = sum(x.balance for x in po_ids)
    #         line_no = line_no_obj.create({
    #             'order_id': self.id,
    #             'invoice_id': one.id,
    #             'advance_residual': advance_residual,
    #             'advance_residual2': advance_residual2,
    #             'amount_payment_org': amount_payment_org
    #         })
    #         line_no.amount_payment_can_approve_all_this_time = line_no.invoice_id.amount_payment_can_approve_all
    #         line_no.invoice_residual_this_time = line_no.invoice_residual
    #         self.write({'line_no_other_ids': [(4, line_no.id)]})
    #     self.reconcile_order_id = yfhxd
    #     form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new')
    #     return {
    #         'name': u'应付核销单',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'account.reconcile.order',
    #         'type': 'ir.actions.act_window',
    #         'views': [(form_view.id, 'form')],
    #         'res_id': self.reconcile_order_id.id,
    #         'target': 'current',
    #         'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
    #     }

    def create_yshxd(self):
        # self.ensure_one()
        sfk_type = 'yshxd'
        domain = [('code', '=', 'ysdrl'), ('company_id', '=', self.env.user.company_id.id)]
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        journal = self.env['account.journal'].search(domain, limit=1)
        account_obj = self.env['account.account']
        bank_account = account_obj.search(
            [('code', '=', '10021'), ('company_id', '=', self.env.user.company_id.id)],
            limit=1)

        name_title = self.name_title
        invoice_partner = self.invoice_partner
        yshxd = self.env['account.reconcile.order'].create({
            'partner_id': self.partner_id.id,
            'manual_payment_currency_id': self.currency_id.id,
            'invoice_ids': [(4, self.id)],
            'payment_type': 'outbound',
            'name_title': name_title,
            'invoice_partner': invoice_partner,

            # 'fk_journal_id': self.fk_journal_id.id,
            # 'bank_id': self.bank_id.id,
            'partner_type': 'customer',
            'sfk_type': 'yshxd',
            'be_renling': True,
            'name': name,
            'journal_id': journal.id,
            # 'expense_sheet_id': self.expense_sheet_id.id,  # 1009
            'payment_account_id': bank_account.id,
            'invoice_attribute': self.invoice_attribute,
            'operation_wizard': '10',
            'hxd_type_new': '20',
            'yjzy_type': 'other_payment_sale',

        })
        self.reconcile_order_id = yshxd
        # yfhxd._make_lines_po_from_expense()
        yshxd.make_line_no()
        yshxd.action_manager_approve_stage()
        # yfhxd.create_rcfkd()

        form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_new')
        return {
            'name': u'应收款核销单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.reconcile.order',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': self.reconcile_order_id.id,
            'target': 'current',
            'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }

    def submit_yshxd(self):
        print('invoice_ids', self.ids)
        sfk_type = 'yshxd'
        domain = [('code', '=', 'ysdrl'), ('company_id', '=', self.env.user.company_id.id)]
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        journal = self.env['account.journal'].search(domain, limit=1)
        account_obj = self.env['account.account']
        bank_account = account_obj.search([('code', '=', '10021'), ('company_id', '=', self.env.user.company_id.id)],
                                          limit=1)
        form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_new')
        invoice_dic = []
        for one in self:
            for x in one.yjzy_invoice_ids:
                invoice_dic.append(x.id)  # 参考
            invoice_dic.append(one.id)
        print('invoice_dic[k]', invoice_dic)
        # test = [(for x in line.yjzy_invoice_all_ids) for line in self)]
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.reconcile.order',
            'views': [(form_view.id, 'form')],
            'target': 'current',
            'context': {
                'default_invoice_ids': self.ids,  # [line.id for line in self],
                'default_partner_id': self[0].partner_id.id,
                'default_manual_payment_currency_id': self[0].currency_id.id,
                'default_payment_type': 'inbound',
                'default_partner_type': 'customer',
                'default_sfk_type': 'yshxd',
                'default_be_renling': True,
                'default_name': name,
                'default_journal_id': journal.id,
                'default_payment_account_id': bank_account.id,
                'default_operation_wizard': '03',
                'default_hxd_type_new': '20'
            }
        }

    # 定稿，从发票多选创建应付申请 不用了
    def submit_yfhxd(self, attribute):
        print('invoice_ids', self.ids)
        print('partner_id', len(self.mapped('partner_id')))
        if attribute != 'other_payment' and len(self.mapped('partner_id')) > 1:
            raise Warning('不同供应商')
        elif attribute == 'other_payment' and len(self) > 1:
            raise Warning('其他应付不允许多个一起申请付款')
        # ctx = self.context.get('invoice_attribute')
        sfk_type = 'yfhxd'
        domain = [('code', '=', 'yfdrl'), ('company_id', '=', self.env.user.company_id.id)]
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        journal = self.env['account.journal'].search(domain, limit=1)
        account_obj = self.env['account.account']
        bank_account = account_obj.search([('code', '=', '10021'), ('company_id', '=', self.env.user.company_id.id)],
                                          limit=1)
        form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new')

        # for line in self:
        #     for x in line.yjzy_invoice_all_ids:
        #         test = x.id
        invoice_dic = []
        for one in self:
            for x in one.yjzy_invoice_wait_payment_ids:  # 参考M2M的自动多选
                invoice_dic.append(x.id)
            if one.amount_payment_can_approve_all != 0:  # 考虑已经提交审批的申请
                invoice_dic.append(one.id)
        print('invoice_dic[k]', invoice_dic)
        # test = [(for x in line.yjzy_invoice_all_ids) for line in self)]
        # print('ctx',ctx)
        if attribute != 'other_payment':
            operation_wizard = '03'
        else:
            operation_wizard = '10'

        if attribute != 'other_payment':
            return {
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.reconcile.order',
                'views': [(form_view.id, 'form')],
                'target': 'current',
                'context': {
                    'default_invoice_ids': invoice_dic,  # self.yjzy_invoice_all_ids,#
                    'default_partner_id': self[0].partner_id.id,
                    'default_manual_payment_currency_id': self[0].currency_id.id,
                    'default_payment_type': 'outbound',
                    'default_partner_type': 'supplier',
                    'default_sfk_type': 'yfhxd',
                    'default_be_renling': True,
                    'default_name': name,
                    'default_journal_id': journal.id,
                    'default_payment_account_id': bank_account.id,
                    'default_operation_wizard': operation_wizard,
                    'default_hxd_type_new': '40',
                    'purchase_code_balance': 1,
                    'default_invoice_attribute': attribute,
                    'default_invoice_partner': self[0].invoice_partner,
                    'default_name_title': self[0].name_title
                }
            }

    # 创建应收 等待定稿
    def create_yshxd_from_multi_invoice(self, attribute):
        print('invoice_ids', self.ids)
        state_draft = len(self.filtered(lambda x: x.state != 'open'))
        print('state_draft', state_draft)
        print('attribute', attribute)
        if attribute != 'other_payment' and len(self.mapped('partner_id')) > 1:
            raise Warning('不同供应商')
        elif attribute == 'other_payment' and len(self) > 1:
            raise Warning('其他应付不允许多个一起申请付款')
        elif state_draft >= 1:
            raise Warning('非确认账单不允许创建付款申请')
        sfk_type = 'yshxd'
        domain = [('code', '=', 'ysdrl'), ('company_id', '=', self.env.user.company_id.id)]
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        journal = self.env['account.journal'].search(domain, limit=1)
        account_obj = self.env['account.account']
        bank_account = account_obj.search([('code', '=', '10021'), ('company_id', '=', self.env.user.company_id.id)],
                                          limit=1)
        form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_other_payment_simple')
        invoice_dic = []
        account_reconcile_order_obj = self.env['account.reconcile.order']
        yjzy_payment_id = self.env.context.get('default_yjzy_payment_id')
        print('yjzy_payment_id___11111', yjzy_payment_id)
        operation_wizard = '10'
        for one in self:
            for x in one.yjzy_invoice_wait_payment_ids:  # 参考M2M的自动多选
                invoice_dic.append(x.id)
            if one.amount_payment_can_approve_all != 0:  # 考虑已经提交审批的申请
                invoice_dic.append(one.id)
        print('invoice_dic', invoice_dic)
        yshxd = self.env['account.reconcile.order'].create({
            'partner_id': self[0].partner_id.id,
            'manual_payment_currency_id': self[0].currency_id.id,
            'invoice_ids': [(6, 0, invoice_dic)],
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'sfk_type': 'yshxd',
            'be_renling': True,
            'name': name,
            'journal_id': journal.id,
            'payment_account_id': bank_account.id,
            'operation_wizard': operation_wizard,
            'hxd_type_new': '20',
            'invoice_attribute': attribute,
            'yjzy_payment_id': yjzy_payment_id,
            'invoice_type_main': self[0].invoice_type_main,
            'invoice_partner': self[0].invoice_partner,
            'name_title': self[0].name_title
            # 'invoice_partner': self[0].invoice_partner,
            # 'name_title': self[0].name_title
        })
        yshxd.make_lines()
        if attribute == 'other_payment':
            for x in yshxd.line_no_ids:
                if x.invoice_residual >= yshxd.yjzy_payment_balance:
                    x.amount_payment_org = yshxd.yjzy_payment_balance
                else:
                    x.amount_payment_org = x.invoice_residual
            for x in yshxd.line_ids:
                if x.amount_invoice_so_residual >= yshxd.yjzy_payment_balance:
                    x.amount_payment_org = yshxd.yjzy_payment_balance
                else:
                    x.amount_payment_org = x.amount_invoice_so_residual
            print('test_qeqwe', yshxd)

        return {
            'name': u'应收核销单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.reconcile.order',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': yshxd.id,
            'target': 'new',
            'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }

    # #1228单独直接从发票创建应付核销单
    #   def action_create_yfhxd_from_one_invoce(self):
    #       ctx = self.env.context.get('invoice_attribute')
    #       hxd = self.create_yfhxd_from_multi_invoice(ctx)
    #
    #       return hxd

    # 1209定稿
    def action_create_yfhxd(self):
        ctx = self.env.context.get('invoice_attribute')
        yjzy_payment_id = self.env.context.get('yjzy_payment_id')
        print('yjzy_payment_id', yjzy_payment_id)
        hxd = False
        if self.type == 'in_invoice':
            hxd = self.create_yfhxd_from_multi_invoice(ctx)
        elif self.type == 'out_invoice':
            hxd = self.with_context({'default_yjzy_payment_id': yjzy_payment_id}).create_yshxd_from_multi_invoice(ctx)
        return hxd

    # 1209定稿 ok1218
    def create_yfhxd_from_multi_invoice(self, attribute):
        print('invoice_ids', self.ids)
        print('partner_id', len(self.mapped('partner_id')))
        state_draft = len(self.filtered(lambda x: x.state != 'open'))
        print('state_draft', state_draft)
        hxd_line_approval_ids = self.env['account.reconcile.order.line.no'].search(
            [('invoice_id.id', 'in', self.ids), ('order_id.state', 'not in', ['done', 'approved'])])
        order_id = hxd_line_approval_ids.mapped('order_id')
        print('xd_line_approval_ids[0]_akiny', order_id)
        # 如果有存在审批中的账单，可以跳转对应的申请单
        if hxd_line_approval_ids:
            view = self.env.ref('sh_message.sh_message_wizard_1')
            view_id = view and view.id or False
            context = dict(self._context or {})
            context['message'] = "选择的应付账单，有存在审批中的，请查验"
            context['res_model'] = "account.reconcile.order"
            context['res_id'] = order_id[0].id
            context['views'] = self.env.ref('yjzy_extend.account_yfhxd_form_view_new').id
            context['no_advance'] = True
            print('context_akiny', context)
            return {
                'name': 'Success',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sh.message.wizard',
                'views': [(view_id, 'form')],
                'target': 'new',
                'context': context,
            }
        print('akiny_test', len(self.mapped('invoice_attribute')), len(self.mapped('yjzy_type')),
              len(self.mapped('invoice_type_main')))
        # if attribute != 'other_payment' and len(self.mapped('partner_id')) > 1:
        #     raise Warning('不同供应商')
        if len(self) > 1:  # attribute == 'other_payment' and
            raise Warning('不允许多张应付一起申请')
        if state_draft >= 1:
            raise Warning('非确认账单不允许创建付款申请')


        sfk_type = 'yfhxd'
        domain = [('code', '=', 'yfdrl'), ('company_id', '=', self.env.user.company_id.id)]
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        journal = self.env['account.journal'].search(domain, limit=1)
        account_obj = self.env['account.account']
        bank_account = account_obj.search([('code', '=', '10021'), ('company_id', '=', self.env.user.company_id.id)],
                                          limit=1)
        form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new')
        invoice_dic = []
        account_reconcile_order_obj = self.env['account.reconcile.order']
        for one in self:
            if one.amount_payment_can_approve_all == 0:
                raise Warning('可申请付款金额为0，不允许提交！')
            for x in one.yjzy_invoice_wait_payment_ids:  # 参考M2M的自动多选  剩余应付金额！=0的额外账单
                invoice_dic.append(x.id)
            print('amount_payment_can_approve_all_akiny', one.amount_payment_can_approve_all)
            if one.amount_payment_can_approve_all != 0:  # 考虑已经提交审批的申请
                invoice_dic.append(one.id)
        print('invoice_dic', invoice_dic)
        account_reconcile_id = account_reconcile_order_obj.create({
            'partner_id': self[0].partner_id.id,
            'manual_payment_currency_id': self[0].currency_id.id,
            'invoice_ids': [(6, 0, invoice_dic)],
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'sfk_type': 'yfhxd',
            'be_renling': True,
            'name': name,
            'journal_id': journal.id,
            'payment_account_id': bank_account.id,
            'yjzy_type': self[0].yjzy_type_1,  # 1207akiny
            'purchase_code_balance': 1,
            'invoice_attribute': attribute,
            'invoice_type_main': self[0].invoice_type_main,
            'invoice_partner': self[0].invoice_partner,
            'name_title': self[0].name_title
        })
        if account_reconcile_id.invoice_attribute in ['other_po', 'expense_po', 'other_payment']:
            account_reconcile_id.operation_wizard = '10'
            account_reconcile_id.hxd_type_new = '40'
            account_reconcile_id.make_lines()
            stage_id = account_reconcile_id._stage_find(domain=[('code', '=', '030')])
            account_reconcile_id.write({'stage_id': stage_id.id, })
            # account_reconcile_id.make_lines()
        else:
            if account_reconcile_id.supplier_advance_payment_ids_count == 0:  # 如果相关的预付单数量=0，跳过第一步的预付认领
                account_reconcile_id.operation_wizard = '10'
                account_reconcile_id.hxd_type_new = '40'
                account_reconcile_id.make_lines()
                stage_id = account_reconcile_id._stage_find(domain=[('code', '=', '030')])
                account_reconcile_id.write({'stage_id': stage_id.id, })
            else:
                account_reconcile_id.operation_wizard = '03'
                # account_reconcile_id.hxd_type_new = '40'#以前是40 1218删除
                account_reconcile_id.hxd_type_new = '40'
                # account_reconcile_id.make_lines()#1220
                # account_reconcile_id.line_ids.unlink() 1218删除
                account_reconcile_id.make_line_no()  # 1220
                account_reconcile_id.make_account_payment_state_ids()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.reconcile.order',
            'views': [(form_view.id, 'form')],
            'res_id': account_reconcile_id.id,
            'target': 'current',
            'context': {'default_sfk_type': 'yfhxd',
                        'show_po': 1,
                        }
        }

    def action_create_yfhxd_advance(self):
        ctx = self.env.context.get('invoice_attribute')
        yjzy_payment_id = self.env.context.get('yjzy_payment_id')
        print('yjzy_payment_id', yjzy_payment_id)
        hxd = False
        if self.type == 'in_invoice':
            hxd = self.create_yfhxd_from_multi_invoice_advance(ctx)
        elif self.type == 'out_invoice':
            hxd = self.with_context({'default_yjzy_payment_id': yjzy_payment_id}).create_yshxd_from_multi_invoice(ctx)
        return hxd

    def open_other_payment_reconcile_order_ids(self):
        form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new')
        tree_view = self.env.ref('yjzy_extend.account_yfhxd_tree_view_approve_new')

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.reconcile.order',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'target': 'current',
            'domain': [('invoice_ids', 'in', self.id)],
            'context': {}
        }

    def open_invoice_ids(self):
        tree_view = self.env.ref('yjzy_extend.invoice_new_1_tree')
        form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        self.ensure_one()
        return {
            'name': u'额外账单',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'target': 'current',
            'domain': [('yjzy_invoice_id', '=', self.id)]
        }

    def open_invoice_ids_new(self):
        ctx = self.env.context.get('invoice_type')
        if ctx == 'sale':
            tree_view = self.env.ref('yjzy_extend.invoice_new_1_tree')
            form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        else:
            tree_view = self.env.ref('yjzy_extend.view_supplier_invoice_extra_tree')
            form_view = self.env.ref('yjzy_extend.view_account_supplier_invoice_new_form')
        self.ensure_one()
        return {
            'name': u'额外账单',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'target': 'new',
            'domain': [('yjzy_invoice_id', '=', self.id), ('invoice_attribute', '=', 'extra')],
            'context': {'open_from_normal': 1}
        }

    def open_invoice_ids_new_all(self):
        ctx = self.env.context.get('invoice_type')
        if ctx == 'sale':
            tree_view = self.env.ref('yjzy_extend.invoice_new_1_tree')
            form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        else:
            tree_view = self.env.ref('yjzy_extend.view_supplier_invoice_extra_tree')
            form_view = self.env.ref('yjzy_extend.view_account_supplier_invoice_new_form')
        self.ensure_one()
        return {
            'name': u'所有账单',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'target': 'new',
            'domain': [('yjzy_invoice_id', '=', self.id), ('invoice_attribute', 'in', ['extra', 'normal'])],
            'context': {'open_from_normal': 1}
        }

    def open_customer_invoice_id(self):
        form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        print('test', self.payment_term_id, self.currency_id)
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'views': [(form_view.id, 'form')],
            'target': 'current',
            'context': {
                'default_yjzy_invoice_id': self.id,  # [line.id for line in self],
                'default_partner_id': self.partner_id.id,
                'default_type': 'out_invoice',
                'only_ref': 1,
                'type': 'out_invoice',
                'journal_type': 'sale',
                'default_yjzy_type': 'sale',
                'is_yjzy_invoice': True,
                'yjzy_invoice_number': self.number,
                'default_is_yjzy_invoice': True,
                'default_payment_term_id': self.payment_term_id.id,
                'default_currency_id': self.currency_id.id,
                'default_include_tax': self.include_tax,
                'default_date_ship': self.date_ship,
                'default_date_finish': self.date_finish,
                'default_date_invoice': self.date_invoice,
                'default_date': self.date,
                'default_date_out_in': self.date_out_in,
                'default_bill_id': self.bill_id.id,
                'default_gongsi_id': self.gongsi_id.id,
                'default_yjzy_payment_term_id': self.payment_term_id.id,
                'default_yjzy_currency_id': self.currency_id.id,
            }
        }

    @api.onchange('yjzy_invoice_id')
    def onchange_yjzy_invoice_id(self):
        self.compute_name_extra()
        self.partner_id = self.yjzy_invoice_id.partner_id
        self.payment_term_id = self.yjzy_invoice_id.payment_term_id
        self.currency_id = self.yjzy_invoice_id.currency_id
        self.include_tax = self.yjzy_invoice_id.include_tax
        self.date_ship = self.yjzy_invoice_id.date_ship
        self.date_finish = self.yjzy_invoice_id.date_finish
        self.date_invoice = self.yjzy_invoice_id.date_invoice
        self.date = self.yjzy_invoice_id.date
        self.date_out_in = self.yjzy_invoice_id.date_out_in
        self.bill_id = self.yjzy_invoice_id.bill_id
        self.gongsi_id = self.yjzy_invoice_id.gongsi_id
        self.yjzy_payment_term_id = self.yjzy_invoice_id.payment_term_id
        self.yjzy_currency_id = self.yjzy_invoice_id.currency_id

    def open_supplier_invoice_id(self):
        form_view = self.env.ref('yjzy_extend.view_account_supplier_invoice_new_form')
        print('test', self.payment_term_id, self.currency_id)
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'views': [(form_view.id, 'form')],
            'target': 'current',
            'context': {
                'default_yjzy_invoice_id': self.id,  # [line.id for line in self],
                'default_partner_id': self.partner_id.id,
                'default_type': 'in_invoice',
                'only_ref': 1,
                'type': 'in_invoice',
                'journal_type': 'purchase',
                'default_yjzy_type': 'purchase',
                'is_yjzy_invoice': True,
                'yjzy_invoice_number': self.number,
                'default_is_yjzy_invoice': True,
                'default_payment_term_id': self.payment_term_id.id,
                'default_currency_id': self.currency_id.id,
                'default_include_tax': self.include_tax,
                'default_date_ship': self.date_ship,
                'default_date_finish': self.date_finish,
                'default_date_invoice': self.date_invoice,
                'default_date': self.date,
                'default_date_out_in': self.date_out_in,
                'default_bill_id': self.bill_id.id,
                'default_gongsi_id': self.gongsi_id.id,
                'default_yjzy_payment_term_id': self.payment_term_id.id,
                'default_yjzy_currency_id': self.currency_id.id,
            }
        }

    def open_customer_refund_id(self):
        form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        print('test', self.payment_term_id, self.currency_id)
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'views': [(form_view.id, 'form')],
            'target': 'current',
            'context': {
                'default_yjzy_invoice_id': self.id,  # [line.id for line in self],
                'default_partner_id': self.partner_id.id,
                'default_type': 'out_refund',
                'only_ref': 1,
                'type': 'out_refund',
                'journal_type': 'sale',
                'default_yjzy_type': 'sale',
                'is_yjzy_invoice': True,
                'yjzy_invoice_number': self.number,
                'default_is_yjzy_invoice': True,
                'default_payment_term_id': self.payment_term_id.id,
                'default_currency_id': self.currency_id.id,
                'default_include_tax': self.include_tax,
                'default_date_ship': self.date_ship,
                'default_date_finish': self.date_finish,
                'default_date_invoice': self.date_invoice,
                'default_date': self.date,
                'default_date_out_in': self.date_out_in,
                'default_bill_id': self.bill_id.id,
                'default_gongsi_id': self.gongsi_id.id,
                'default_yjzy_payment_term_id': self.payment_term_id.id,
                'default_yjzy_currency_id': self.currency_id.id,
            }
        }

    def open_supplier_refund_id(self):
        form_view = self.env.ref('yjzy_extend.view_account_supplier_invoice_new_form')
        print('test', self.payment_term_id, self.currency_id)
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'views': [(form_view.id, 'form')],
            'target': 'current',
            'context': {
                'default_yjzy_invoice_id': self.id,  # [line.id for line in self],
                'default_partner_id': self.partner_id.id,
                'default_type': 'in_refund',
                'only_ref': 1,
                'type': 'in_refund',
                'journal_type': 'purchase',
                'default_yjzy_type': 'purchase',
                'is_yjzy_invoice': True,
                'yjzy_invoice_number': self.number,
                'default_is_yjzy_invoice': True,
                'default_payment_term_id': self.payment_term_id.id,
                'default_currency_id': self.currency_id.id,
                'default_include_tax': self.include_tax,
                'default_date_ship': self.date_ship,
                'default_date_finish': self.date_finish,
                'default_date_invoice': self.date_invoice,
                'default_date': self.date,
                'default_date_out_in': self.date_out_in,
                'default_bill_id': self.bill_id.id,
                'default_gongsi_id': self.gongsi_id.id,
                'default_yjzy_payment_term_id': self.payment_term_id.id,
                'default_yjzy_currency_id': self.currency_id.id,
            }
        }

    # @api.multi
    # def write(self, vals):
    #
    #     for one in self:
    #         one.payment_term_id = one.yjzy_payment_term_id
    #     return super(account_invoice, self).write(vals)

    def invoice_assign_outstanding_credit(self):
        self.ensure_one()
        # 没审核的分录不能核销
        if self.type == 'out_refund':
            lines = self.move_line_ids + self.yjzy_invoice_id.move_line_ids
            todo_lines = lines.filtered(
                lambda x: (x.plan_invoice_id == self.yjzy_invoice_id or x.invoice_id == self.yjzy_invoice_id)
                          and x.reconciled == False and x.account_id.code == '1122')
            print('todo', todo_lines, self.yjzy_invoice_id)
            for todo in todo_lines:
                self.assign_outstanding_credit(todo.id)
        elif self.type == 'in_refund':
            lines = self.move_line_ids + self.yjzy_invoice_id.move_line_ids
            todo_lines = lines.filtered(
                lambda x: (x.plan_invoice_id == self.yjzy_invoice_id or x.invoice_id == self.yjzy_invoice_id)
                          and x.reconciled == False and x.account_id.code == '2202')
            print('todo', todo_lines, self.yjzy_invoice_id)
            for todo in todo_lines:
                self.assign_outstanding_credit(todo.id)

    def back_tax_assign_outstanding_credit(self):
        self.ensure_one()
        # 没审核的分录不能核销

        lines = self.move_line_ids + self.yjzy_invoice_id.move_line_ids
        todo_lines = lines.filtered(
            lambda x: (x.plan_invoice_id == self.yjzy_invoice_id or x.invoice_id == self.yjzy_invoice_id)
                      and x.reconciled == False and x.account_id.code == '1122')
        print('todo', todo_lines, self.yjzy_invoice_id)
        for todo in todo_lines:
            self.assign_outstanding_credit(todo.id)

    def _stage_find(self, domain=None, order='sequence'):
        search_domain = list(domain)
        return self.env['account.invoice.stage'].search(search_domain, order=order, limit=1)

    def stage_action_draft(self):
        stage_id = self._stage_find(domain=[('code', '=', '001')])
        self.stage_id = stage_id.id
        self.action_invoice_draft()

    def stage_action_submit(self):
        stage_id = self._stage_find(domain=[('code', '=', '002')])
        self.stage_id = stage_id.id

    def stage_action_approved(self):
        stage_id = self._stage_find(domain=[('code', '=', '003')])
        self.stage_id = stage_id.id

    def stage_action_done(self):
        stage_id = self._stage_find(domain=[('code', '=', '004')])
        self.stage_id = stage_id.id
        self.action_invoice_open()
        self.invoice_assign_outstanding_credit()

    def action_invoice_open(self):
        res = super(account_invoice, self).action_invoice_open()
        for inv_1 in self:
            stage_id = inv_1._stage_find(domain=[('code', '=', '004')])
            inv_1.stage_id = stage_id
        return res

    @api.multi
    def action_invoice_paid(self):
        # lots of duplicate calls to action_invoice_paid, so we remove those already paid
        to_pay_invoices = self.filtered(lambda inv: inv.state != 'paid')
        if to_pay_invoices.filtered(lambda inv: inv.state != 'open'):
            raise UserError(_('Invoice must be validated in order to set it to register payment.'))
        if to_pay_invoices.filtered(lambda inv: not inv.reconciled):
            raise UserError(
                _('You cannot pay an invoice which is partially paid. You need to reconcile payment entries first.'))

        stage_id = self._stage_find(domain=[('code', '=', '008')])

        return to_pay_invoices.write({'state': 'paid',
                                      'stage_id': stage_id.id})

    def manual_stage_id(self):
        if self.state == 'open':
            self.stage_id = self._stage_find(domain=[('code', '=', '004')])
        elif self.state == 'draft':
            self.stage_id = self._stage_find(domain=[('code', '=', '001')])
        elif self.state == 'cancel':
            self.stage_id = self._stage_find(domain=[('code', '=', '006')])
        else:
            self.stage_id = self._stage_find(domain=[('code', '=', '008')])

    def stage_action_pending(self):
        stage_id = self._stage_find(domain=[('code', '=', '007')])
        self.stage_id = stage_id

    def stage_action_back_pending(self):
        stage_id = self._stage_find(domain=[('code', '=', '004')])
        self.stage_id = stage_id

    def stage_action_refuse(self, reason):
        stage_id = self._stage_find(domain=[('code', '=', '005')])
        self.stage_id = stage_id.id
        if self.state == 'open':
            self.action_invoice_cancel()
            self.action_invoice_draft()
        for invoice in self:
            invoice.message_post_with_view('yjzy_extend.account_invoice_template_refuse_reason',
                                           values={'reason': reason, 'name': self.tb_contract_code},
                                           subtype_id=self.env.ref(
                                               'mail.mt_note').id)

    def stage_action_cancel(self):
        stage_id = self._stage_find(domain=[('code', '=', '006')])
        self.stage_id = stage_id.id
        if self.state == 'paid':
            raise Warning('已经支付的合同不允许取消')
        if self.state == 'open':
            self.action_invoice_cancel()

    def open_invoice_extra(self):
        """ Utility method used to add an "Open Parent" button in partner views """
        self.ensure_one()
        invoice_extra_form_id = self.env.ref('yjzy_extend.view_customer_invoice_extra_form').id

        return {
            'name': _(u'额外账单'),
            'view_type': 'form',
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'res_model': 'account.invoice',
            'views': [(invoice_extra_form_id, 'form')],
            'res_id': self.id,
            'target': 'current',
            'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }

    def open_reconcile_order_line(self):
        self.ensure_one()
        # form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        state = self.env.context.get('state') or 'done'
        for one in self:
            if one.type == 'out_invoice':
                tree_view = self.env.ref('yjzy_extend.account_yshxd_line_tree_view')
                name = '客户应收'
            if one.type == 'in_invoice':
                tree_view = self.env.ref('yjzy_extend.account_yfhxd_line_tree_view')
                name = '供应商应付'
            return {
                'name': name,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.reconcile.order.line',
                'type': 'ir.actions.act_window',
                'views': [(tree_view.id, 'tree')],
                'domain': [('invoice_id', 'in', [one.id]), ('order_id.state', '=', state)],
                'target': 'new'
            }

    def open_reconcile_order_no_line(self):
        self.ensure_one()
        advance = self.env.context.get('advance') or 0
        ctx = {'advance': advance}
        if advance:
            test = 'amount_advance_org_compute'
        else:
            test = 'amount_payment_org'
        print('pay_type_akiny', advance)
        # form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        state = self.env.context.get('state') or 'done'
        for one in self:
            if one.type == 'out_invoice':
                tree_view = self.env.ref('yjzy_extend.account_yshxd_line_no_tree_view_new')
                name = '客户应收'

            if one.type == 'in_invoice':
                tree_view = self.env.ref('yjzy_extend.account_yfhxd_line_no_tree_view')
                name = '供应商应付'
            return {
                'name': name,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.reconcile.order.line.no',
                'type': 'ir.actions.act_window',
                'views': [(tree_view.id, 'tree')],
                'domain': [('invoice_id', 'in', [one.id]), ('order_id.state', '=', state), (test, '!=', 0)],
                'target': 'new',
                'context': ctx

            }

    def open_reconcile_order(self):
        self.ensure_one()
        # form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        state = self.env.context.get('state') or 'done'
        advance = self.env.context.get('advance') or 0
        ctx = {'advance': advance}
        if advance:
            test = 'amount_advance_org_new'
            reconcile_order_id = self.env['account.reconcile.order'].search(
                [('invoice_id', '=', self.id), ('state', 'in', ['posted', 'draft']), ('hxd_type_new', '=', '30')],
                limit=1)
        else:
            test = 'amount_payment_org_new'
            reconcile_order_id = self.env['account.reconcile.order'].search(
                [('invoice_id', '=', self.id), ('state', 'in', ['posted', 'draft']), ('hxd_type_new', '=', '40')],
                limit=1)
        print('pay_type_akiny', advance, test)
        if self.type == 'out_invoice':
            tree_view = self.env.ref('yjzy_extend.account_yshxd_tree_view_new')
            form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_new')
            name = '客户应收'

        if self.type == 'in_invoice':
            tree_view = self.env.ref('yjzy_extend.account_yfhxd_tree_view_new')
            form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new')
            name = '供应商应付'
            if not reconcile_order_id:
                raise Warning('没有审批中的应付申请')
        return {
            'name': name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.reconcile.order',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': reconcile_order_id.id,
            'target': 'new',
            # 'context': ctx

        }

    def open_account_payment_hexiao(self):
        self.ensure_one()

        hexiao_id = self.env['account.payment'].search(
            [('sfk_type', 'in', ['reconcile_yingshou', 'reconcile_yingfu']), ('invoice_log_id', '=', self.id),
             ('state', 'in', ['posted', 'reconciled'])], limit=1)

        if self.type == 'out_invoice':
            form_view = self.env.ref('yjzy_extend.view_ysrld_reconcile_form')
            name = '应收核销'

        if self.type == 'in_invoice':
            form_view = self.env.ref('yjzy_extend.view_ysrld_reconcile_form')
            name = '应付核销'
            if not hexiao_id:
                raise Warning('没有完成的核销单')
        return {
            'name': name,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': hexiao_id.id,
            'target': 'new',
            # 'context': ctx

        }

    def open_supplier_reconcile_order_line(self):
        self.ensure_one()
        # form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.account_yfhxd_line_tree_view_new')
        for one in self:
            return {
                'name': u'已完成的应付认领明细',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.reconcile.order.line',
                'type': 'ir.actions.act_window',
                'views': [(tree_view.id, 'tree')],
                'domain': [('order_id.state', '=', 'done'), '|', ('invoice_id', 'in', [one.id]),
                           ('yjzy_invoice_id', 'in', [one.yjzy_invoice_id.id])],
                'target': 'new'
            }

    @api.multi
    def name_get(self):
        # show_date_finish = self.env.context.get('show_date_finish')
        supplier_delivery_date = self.env.context.get('supplier_delivery_date')
        # print('=112====', show_date_finish)
        res = []
        for one in self:
            purchase_date_finish_state = one.purchase_date_finish_state
            if one.purchase_date_finish_state == 'draft':
                purchase_date_finish_state = '草稿'
            if one.purchase_date_finish_state == 'submit':
                purchase_date_finish_state = '待审批'
            if one.purchase_date_finish_state == 'done':
                purchase_date_finish_state = '完成'
            # if show_date_finish:
            #     if one.date_finish:
            #         name = '%s %s' % (
            #             one.date_finish or '', one.partner_id.name or '',)
            #     else:
            #         name = '%s %s' % (
            #             '无交单日', one.partner_id.name or '',)
            if supplier_delivery_date:
                if one.supplier_delivery_date:
                    name = '%s %s' % (
                        one.supplier_delivery_date or '', one.partner_id.name or '',)
                else:
                    name = '%s %s' % (
                        '无发货日', one.partner_id.name or '',)

            else:
                name = '%s[%s]' % (one.tb_contract_code, str(one.residual))
            res.append((one.id, name))
        print('=111====', res)
        return res

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
            if not one.purchase_date_finish_att:
                raise Warning('请提交附件')
            one.purchase_date_finish_state = 'done'  # 直接一步完成

    def action_purchase_date_finish_state_done(self):
        for one in self:
            if self.env.ref('akiny.group_trans_hegui') not in self.env.user.groups_id:
                raise Warning('您没有审批的权限！')
            else:
                one.purchase_date_finish_state = 'done'

    def action_purchase_date_finish_state_refuse(self):
        for one in self:
            one.purchase_date_finish_state = 'refuse'

    def auto_account_invoice_open(self):
        today = datetime.today()
        strptime = datetime.strptime
        company_after_date_out_in_times = self.company_id.after_date_out_in_times
        for one in self:
            if one.date_out_in:
                after_date_out_in_times = today - strptime(one.date_out_in, DF)
                if after_date_out_in_times >= company_after_date_out_in_times and one.bill_id.sale_type != 'proxy':
                    one.action_invoice_open()

    @api.multi
    def action_invoice_cancel_1(self):
        if self.filtered(lambda inv: inv.state not in ['draft', 'open', 'paid']):
            raise UserError(_("Invoice must be in draft or open state in order to be cancelled."))
        return self.action_cancel()

    # 1126 前的备份
    def action_create_yfhxd_old(self):
        ctx = self.env.context.get('invoice_attribute')
        yjzy_payment_id = self.env.context.get('yjzy_payment_id')
        print('yjzy_payment_id', yjzy_payment_id)
        hxd = False
        if self.type == 'in_invoice':
            hxd = self.create_yfhxd_from_multi_invoice(ctx)
        elif self.type == 'out_invoice':
            hxd = self.with_context({'default_yjzy_payment_id': yjzy_payment_id}).create_yshxd_from_multi_invoice(ctx)
        return hxd

    # 1126前的备份
    def create_yfhxd_from_multi_invoice_old(self, attribute):
        print('invoice_ids', self.ids)
        print('partner_id', len(self.mapped('partner_id')))
        state_draft = len(self.filtered(lambda x: x.state != 'open'))
        print('state_draft', state_draft)
        hxd_line_approval_ids = self.env['account.reconcile.order.line'].search(
            [('invoice_id.id', 'in', self.ids), ('order_id.state', 'not in', ['done', 'approved'])])
        if hxd_line_approval_ids:
            raise Warning('选择的应付账单，有存在审批中的，请查验')
        if attribute != 'other_payment' and len(self.mapped('partner_id')) > 1:
            raise Warning('不同供应商')
        elif attribute == 'other_payment' and len(self) > 1:
            raise Warning('其他应付不允许多个一起申请付款')
        elif state_draft >= 1:
            raise Warning('非确认账单不允许创建付款申请')
        sfk_type = 'yfhxd'
        domain = [('code', '=', 'yfdrl'), ('company_id', '=', self.env.user.company_id.id)]
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        journal = self.env['account.journal'].search(domain, limit=1)
        account_obj = self.env['account.account']
        bank_account = account_obj.search([('code', '=', '10021'), ('company_id', '=', self.env.user.company_id.id)],
                                          limit=1)
        form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new')
        invoice_dic = []
        account_reconcile_order_obj = self.env['account.reconcile.order']
        # for one in self:
        #     for x in one.yjzy_invoice_wait_payment_ids:#参考M2M的自动多选
        #         invoice_dic.append(x.id)
        #     invoice_dic.append(one.id)
        # print('invoice_dic[k]',invoice_dic)
        for one in self:
            for x in one.yjzy_invoice_wait_payment_ids:  # 参考M2M的自动多选  剩余应付金额！=0的额外账单
                invoice_dic.append(x.id)
            if one.amount_payment_can_approve_all != 0:  # 考虑已经提交审批的申请
                invoice_dic.append(one.id)
        print('invoice_dic', invoice_dic)
        # test = [(for x in line.yjzy_invoice_all_ids) for line in self)]
        # invoice_ids = self.env['account.invoice'].search([('id','in',invoice_dic)])
        # with_context(
        #     {'fk_journal_id': 1, 'default_be_renling': 1, 'default_invoice_ids': invoice_dic,
        #      'default_payment_type': 'outbound', 'show_so': 1, 'default_sfk_type': 'yfhxd', }).
        if attribute not in ['other_po', 'expense_po', 'other_payment']:
            operation_wizard = '03'
        else:
            operation_wizard = '10'

        account_reconcile_id = account_reconcile_order_obj.create({
            'partner_id': self[0].partner_id.id,
            'manual_payment_currency_id': self[0].currency_id.id,
            'invoice_ids': [(6, 0, invoice_dic)],
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'sfk_type': 'yfhxd',
            'be_renling': True,
            'name': name,
            'journal_id': journal.id,
            'payment_account_id': bank_account.id,
            'operation_wizard': operation_wizard,
            'hxd_type_new': '40',
            'purchase_code_balance': 1,
            'invoice_attribute': attribute,
            'invoice_partner': self[0].invoice_partner,
            'name_title': self[0].name_title

            # 'partner_id': self.partner_id.id,
            #         'sfk_type': 'yfhxd',
            #         # 'invoice_ids': invoice_ids,
            #         'yjzy_advance_payment_id': self.id,
            #         'payment_type': 'outbound',
            #         'be_renling': 1,
            #         'partner_type': 'supplier',
            #         'operation_wizard': '25',
            #         'hxd_type_new': '30',  # 预付-应付
        })

        account_reconcile_id.make_lines()
        if account_reconcile_id.supplier_advance_payment_ids_count == 0:  # 如果相关的预付单数量=0，跳过第一步的预付认领
            account_reconcile_id.operation_wizard = '10'
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.reconcile.order',
            'views': [(form_view.id, 'form')],
            'res_id': account_reconcile_id.id,
            'target': 'current',
            'context': {'default_sfk_type': 'yfhxd',
                        }
        }

    def compute_advice_advance_amount(self):
        for one in self:
            for x in one.invoice_line_ids:
                x.compute_original_so_po_amount()

    def open_account_reconcile_order(self):
        self.ensure_one()
        if self.invoice_attribute_all_in_one == '120':
            tree_view = self.env.ref('yjzy_extend.account_yfhxd_tree_view_new')
            form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new')
        if self.invoice_attribute_all_in_one == '110':
            tree_view = self.env.ref('yjzy_extend.account_yshxd_tree_view_new')
            form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_new')

        return {
            'name': u'认领单',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.reconcile.order',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('invoice_ids', 'in', self.id)],
            'target': 'new'
        }


class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    @api.depends('sale_line_ids')
    def _compute_so(self):
        for one in self:
            one.so_id = one.sale_line_ids and one.sale_line_ids[0].order_id or False

    @api.depends('price_unit')
    def _compute_amount(self):
        for one in self:
            price_unit = one.price_unit
            price_total = one.price_total
            if one.invoice_id.type in ['in_refund', 'out_refund']:
                yjzy_price_unit = -price_unit

            else:
                yjzy_price_unit = price_unit
            return yjzy_price_unit

    @api.depends('price_unit', 'invoice_id.state', 'quantity')
    def _compute_amount_new(self):
        for one in self:
            price_unit = one.price_unit
            price_total = one.price_total
            if one.invoice_id.type in ['in_refund', 'out_refund']:
                one.yjzy_price_unit = -price_unit

            else:
                one.yjzy_price_unit = price_unit

    @api.depends('invoice_id', 'invoice_id.yjzy_invoice_id')
    def _compute_yjzy_invoice(self):
        for one in self:
            print('yjzy_invoice', one.invoice_id.yjzy_invoice_id)
            if one.invoice_id.yjzy_invoice_id:
                one.yjzy_invoice_id = one.invoice_id.yjzy_invoice_id
            else:
                one.yjzy_invoice_id = one.invoice_id

    @api.depends('yjzy_price_unit', 'quantity', 'invoice_id.state', 'price_unit', )
    def _compute_price_total(self):
        for one in self:
            yjzy_price_total = one.yjzy_price_unit * one.quantity
            one.yjzy_price_total = yjzy_price_total

    # @api.depends('price_total')
    # def compute_back_tax(self):
    #     for one in self:
    #         back_tax_add_this_time = one.price_total / 1.13 * one.back_tax
    #         one.back_tax_add_this_time = back_tax_add_this_time
    # 0911
    # back_tax_add_this_time = fields.Float('本次应生成退税', compute=compute_back_tax)

    @api.depends('purchase_id', 'purchase_id.amount_total', 'purchase_id.real_advance', 'purchase_id.balance_new',
                 'so_id', 'so_id.amount_total', 'so_id.real_advance', 'so_id.balance_new', 'invoice_id', 'invoice_id.type')
    def compute_original_so_po_amount(self):
        for one in self:
            if one.invoice_id.type == 'in_invoice':
                original_so_po_amount = one.purchase_id.amount_total
                real_advance = one.purchase_id.real_advance
                rest_advance_so_po_balance = one.purchase_id.balance_new
                proportion_tb = original_so_po_amount != 0 and one.price_total / original_so_po_amount or 0
                advice_advance_amount = proportion_tb * real_advance
                advice_advance_amount_1 = proportion_tb * rest_advance_so_po_balance
                one.original_so_po_amount = original_so_po_amount
                one.rest_advance_so_po_balance = rest_advance_so_po_balance
                one.proportion_tb = proportion_tb
                one.advice_advance_amount = advice_advance_amount
                one.advice_advance_amount_1 = advice_advance_amount_1

            if one.invoice_id.type == 'out_invoice':
                original_so_po_amount = one.so_id.amount_total
                real_advance = one.so_id.real_advance
                rest_advance_so_po_balance = one.so_id.balance_new
                proportion_tb = original_so_po_amount != 0 and one.price_total / original_so_po_amount or 0
                advice_advance_amount = proportion_tb * real_advance
                advice_advance_amount_1 = proportion_tb * rest_advance_so_po_balance

                one.original_so_po_amount = original_so_po_amount
                one.rest_advance_so_po_balance = rest_advance_so_po_balance
                one.proportion_tb = proportion_tb
                one.advice_advance_amount = advice_advance_amount
                one.advice_advance_amount_1 = advice_advance_amount_1
    #发货前的预付是要全部认领的。在是预付的金额*这次出运/总采购金额


    original_so_po_amount = fields.Monetary('原始订单金额', currency_field='currency_id',
                                            compute=compute_original_so_po_amount)
    rest_advance_so_po_balance = fields.Monetary('原始订单预收预付剩余未认领金额', currency_field='currency_id',
                                                 compute=compute_original_so_po_amount, store=True)
    proportion_tb = fields.Float('本次出运金额占订单比例', compute=compute_original_so_po_amount)
    advice_advance_amount = fields.Monetary('应认领预付', compute=compute_original_so_po_amount, store=True)
    advice_advance_amount_1 = fields.Monetary('建议认领预付', compute=compute_original_so_po_amount, store=True)

    invoice_yjzy_type_1 = fields.Selection(string=u'发票类型', related='invoice_id.yjzy_type_1')
    item_id = fields.Many2one('invoice.hs_name.item', 'Item')
    so_id = fields.Many2one('sale.order', u'销售订单', compute=_compute_so, store=True)

    manual_so_id = fields.Many2one('sale.order', u'手动销售订单')
    manual_po_id = fields.Many2one('purchase.order', u'手动采购订单')
    is_manual = fields.Boolean('是否手动添加', default=False)

    # yjzy_price_unit = fields.Float('新单价',compute=_compute_amount)
    # yjzy_price_total = fields.Float('新总价',compute=_compute_amount)
    yjzy_invoice_id = fields.Many2one('account.invoice', u'原始账单', compute=_compute_yjzy_invoice)
    invoice_attribute = fields.Selection('账单类型', related='invoice_id.invoice_attribute')
    yjzy_price_unit = fields.Float('新单价', compute=_compute_amount_new,
                                   store=True)  # default=lambda self: self._compute_amount()
    yjzy_price_total = fields.Monetary('新总价', compute=_compute_price_total, store=True, currency_field='currency_id')
    tp_po_invoice_line = fields.Many2one('extra.invoice.line', '申请单明细')

    # 先默认将单价绝对值填入原生单价，之后通过invoice的onchange来决定最终的单价是正数还是负数
    @api.onchange('yjzy_price_unit')
    def onchange_yjzy_price_unit(self):
        if self.invoice_id.is_yjzy_invoice:
            self.price_unit = abs(self.yjzy_price_unit)

    def compute_yjzy_price_unit(self):
        for one in self:
            print('price_unit', one.price_unit)
            one.yjzy_price_unit = one.price_unit


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
    # tb_hsname_line_id = fields.Many2one('tbl.hsname',u'报关明细') #817


class invoice_hs_name_all(models.Model):
    _name = 'invoice.hs_name.all'

    hs_id = fields.Many2one('hs.hs', u'品名')
    purchase_amount2_add_this_time = fields.Float(U'本次采购开票金额')

    p_s_add_this_time = fields.Float('本次应收总金额')
    back_tax_add_this_time = fields.Float('本次退税金额')
    invoice_id = fields.Many2one('account.invoice', u'发票')
    tbl_hsname_all_id = fields.Many2one('tbl.hsname.all', '报关汇总明细')


class purchse_invoice_hsname(models.Model):
    _name = 'purchase.invoice.hsname'

    hs_id = fields.Many2one('hs.hs', u'品名')
    invoice_id = fields.Many2one('account.invoice', u'发票')
    partner_id = fields.Many2one('res.partner', '供应商')
    qty2 = fields.Float(u'报关数量')
    price2 = fields.Float(u'报关单价')
    amount2 = fields.Float(u'实际采购金额', digits=dp.get_precision('Money'))
    back_tax_amount2 = fields.Float(u'报关退税金额', digits=dp.get_precision('Money'))
