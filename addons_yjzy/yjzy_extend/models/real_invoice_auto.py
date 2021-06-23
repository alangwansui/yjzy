# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.addons import decimal_precision as dp
from lxml import etree


class RealInvoiceAuto(models.Model):
    _name = 'real.invoice.auto'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '实际发票'
    _order = 'id desc'

    def get_two_float(self, f_str, n):
        f_str = str(f_str)
        a, b, c = f_str.partition('.')
        c = (c + "0" * n)[:n]
        return ".".join([a, c])

    def get_two_float_1(self, f_str, n):
        f_str = str(f_str)
        a, b, c = f_str.partition('.')
        c = (c + "0" * n)[:n]
        return c

    # @api.depends('untaxed_amount', 'tax')
    # def compute_amount_total(self):
    #     for one in self:
    #
    #         amount_total = (1 + one.tax) * one.untaxed_amount
    #         get_two_float_1 = one.get_two_float_1(amount_total, 2)
    #         print('akiny', str(get_two_float_1))
    #         if str(get_two_float_1) == '99':
    #             one.amount_total = round(amount_total, 0)
    #         elif str(get_two_float_1) in ['01', '00']:
    #             one.amount_total = round(amount_total, 0)
    #         else:
    #             one.amount_total = amount_total

    invoice_type = fields.Selection([('10', '增值税电子普通发票'), ('04', '增值税普通发票'), ('01', '增值税专用发票')], '发票类型')
    invoice_code = fields.Char(u'发票代码')
    invoice_number = fields.Char(u'发票号')
    untaxed_amount = fields.Monetary(u'不含税金额', currency_field='company_currency_id')
    date_invoice = fields.Date(u'开票日期')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)

    company_currency_id = fields.Many2one('res.currency', '本币币种',
                                          default=lambda self: self.env.user.company_id.currency_id)

    tax = fields.Float(u'税率', default=0.13)
    amount_total = fields.Monetary(u'含税金额', currency_field='company_currency_id', )

    partner_id = fields.Many2one('res.partner', u'合作伙伴')
    bill_id = fields.Many2one('transport.bill', u'出运单')
    state = fields.Selection([('draft', 'draft'), ('done', 'done')], 'State', track_visibility='onchange',
                             default='draft')
    plan_invoice_auto_id = fields.Many2one('plan.invoice.auto', '应收发票')

    # invoice_ids = fields.Many2many('account.invoice','实际发票')

    @api.onchange('bill_id')
    def onchange_partner_bill(self):
        plan_invoice_auto_ids = self.env['plan.invoice.auto'].search([('bill_id', '=', self.bill_id.id)])
        if len(plan_invoice_auto_ids) > 1:
            raise Warning('一张出运合同对应多个应收发票，请检查！')
        else:
            self.plan_invoice_auto_id = plan_invoice_auto_ids

    def action_confirm(self):
        self.state = 'done'

    def unlink(self):
        if self.state == 'done':
            raise Warning('已经确认的实际发票，不允许删除')
        else:
            return super(RealInvoiceAuto, self).unlink()


class PlanInvoiceAuto(models.Model):
    _name = 'plan.invoice.auto'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '应收发票'
    _order = 'id desc'

    @api.depends('bill_id', 'bill_id.hsname_all_ids')
    def compute_hs_name_all_ids(self):
        for one in self:
            print('akiny', one.bill_id.hsname_all_ids)
            one.hsname_all_ids = one.bill_id.hsname_all_ids

    def _default_plan_invoice_auto_name(self):
        invoice_tenyale_name = self.env.context.get('default_invoice_tenyale_name')
        if invoice_tenyale_name:
            tenyale_name = self.env['ir.sequence'].next_by_code('account.invoice.%s' % invoice_tenyale_name)
        else:
            tenyale_name = self.env['ir.sequence'].next_by_code('account.invoice.tenyale_invoice')
        return tenyale_name

    @api.depends('invoice_ids')
    def compute_currency_id(self):
        for one in self:
            one.currency_id = one.invoice_ids and one.invoice_ids[0].currency_id or self.env.user.company_id.currency_id

    @api.depends('hsname_all_ids', 'hsname_all_ids.plan_invoice_auto_total')
    def compute_plan_invoice_auto_amount(self):
        for one in self:
            one.plan_invoice_auto_amount = sum(x.plan_invoice_auto_total for x in one.hsname_all_ids)

    @api.depends('real_invoice_auto_id', 'real_invoice_auto_id.amount_total')
    def compute_real_invoice_auto_amount(self):
        for one in self:
            one.real_invoice_auto_amount = sum(x.amount_total for x in one.real_invoice_auto_id)

    @api.depends('bill_id', 'bill_id.all_back_tax_invoice_1_ids')
    def compute_back_tax_invoice_ids(self):
        for one in self:
            one.back_tax_invoice_ids = one.bill_id.all_back_tax_invoice_1_ids

    name = fields.Char('name', default=lambda self: self.env['ir.sequence'].next_by_code('plan.invoice.auto.name'))
    invoice_ids = fields.One2many('account.invoice', 'plan_invoice_auto_id', '应付账单')

    currency_id = fields.Many2one('res.currency', u'货币', compute=compute_currency_id, store=True)
    amount_total = fields.Monetary('金额', currency_field='currency_id', store=True)
    bill_id = fields.Many2one('transport.bill', '出运合同', store=True)
    bill_date_out_in = fields.Date('进仓日期', related='bill_id.date_out_in', store=True)
    bill_date_ship = fields.Date('船期', related='bill_id.date_ship', store=True)
    hsname_all_ids = fields.Many2many('tbl.hsname.all', 'pia_id', 'hs_id', 'tbl_id', string='报关明细',
                                      compute='compute_hs_name_all_ids', store=True)
    back_tax_invoice_ids = fields.Many2many('account.invoice', 'pia1_id', 'inv_id', 'tb_id', string='退税账单',
                                            compute=compute_back_tax_invoice_ids)
    state = fields.Selection(
        [('10', '正常待锁定'), ('20', '异常待锁定'), ('30', '已锁定发票未收齐'), ('40', '已锁定异常发票未收齐(锁定一月后)'), ('50', '发票收齐未开票'),
         ('60', '发票收齐已开票'), ('70', '退税未申报'), ('75', '退税部分申报'), ('80', '退税已申报'), ('90', '退税未收齐'), ('100', '退税已收齐')],
        'State', track_visibility='onchange', default='10')

    state_1 = fields.Selection(
        [('10', '报关数据待锁定'), ('20', '报关数据已锁定-应收发票待锁定'), ('30', '应收发票锁定-发票未收齐'), ('40', '发票已收齐-未开销项'),
         ('50', '已开销项-未申报退税'), ('60', '已申报退税未收退税'), ('70','已收退税')],'state_1',track_visibility='onchange',default='10')
    state_2 = fields.Selection(
        [('10', '正常待锁定'), ('20', '异常待锁定'), ('30', '正常待锁定'), ('40', '异常待锁定'), ('50', '正常未收齐'),
         ('60', '异常未收齐'), ('70', '正常未开'), ('75', '异常未开'), ('80', '正常未申报'), ('90', '异常未申报'), ('100', '正常未收'),('110','异常未收'),('120','已收退税')],
        'State', track_visibility='onchange', default='10')

    real_invoice_auto_id = fields.One2many('real.invoice.auto', 'plan_invoice_auto_id', '实际进项发票')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    lock_date = fields.Date('锁定日期')
    plan_invoice_auto_amount = fields.Monetary('应收发票总金额', currency_field='currency_id',
                                               compute=compute_plan_invoice_auto_amount, store=True)
    real_invoice_auto_amount = fields.Monetary('实收发票总金额', currency_field='currency_id',
                                               compute=compute_real_invoice_auto_amount, store=True)

    ciq_amount = fields.Monetary('报关金额', related='bill_id.ciq_amount', currency_field='currency_id',
                                 digits=dp.get_precision('Money'), store=True)
    purchase_amount2_tax_total = fields.Float(u'含税采购金额', related='bill_id.purchase_amount2_tax_total', store=True)
    purchase_amount2_no_tax_total = fields.Float(u'不含税采购金额', related='bill_id.purchase_amount2_no_tax_total', store=True)
    purchase_amount_min_forecast_total = fields.Float('预测采购金额(上限)', digits=(2, 2), related='bill_id.purchase_amount_min_forecast_total',
                                                      store=True)
    purchase_amount_min_add_forecast_total = fields.Float('可增加采购额(上限)', digits=(2, 2),
                                                          related='bill_id.purchase_amount_min_add_forecast_total',
                                                          store=True)
    purchase_amount_min_add_rest_total = fields.Float('采购池(上限)', digits=(2, 2), related='bill_id.purchase_amount_min_add_rest_total',
                                                      store=True)
    purchase_amount2_add_actual_total = fields.Float(U'实际已经增加采购额', related='bill_id.purchase_amount2_add_actual_total', store=True)

    def compute_state_1_2(self):
        for one in self:
            date_ship = one.bill_id.date_ship
            date_out_in = one.bill_id.date_out_in

            state_1 = one.state_1
            state_2 = one.state_2
            today = datetime.today()
            strptime = datetime.strptime
            lock_date = one.lock_date
            back_tax_invoice_ids = one.back_tax_invoice_ids
            back_tax_invoice_declare_ids = back_tax_invoice_ids.filtered(lambda x: x.back_tax_declaration_state == '20')
            back_tax_invoice_residual_0_ids = back_tax_invoice_ids.filtered(lambda x: x.residual != 0)

            date_ship_residual_time = date_ship and (today - strptime(date_ship, DF)).days or 0
            date_out_in_residual_time = date_out_in and (today - strptime(date_out_in, DF)).days or 0
            lock_date_residual_time = lock_date and (today - strptime(lock_date, DF)).days or 0
            plan_invoice_auto_amount = one.plan_invoice_auto_amount
            real_invoice_auto_amount = one.real_invoice_auto_amount
            print('real_invoice_auto_amount',real_invoice_auto_amount)

            if not date_ship:
                one.state_1 = '10'
                one.state_2 = '10'
                if date_out_in_residual_time >= 15:
                    one.state_2 = '20'
                    one.state_1 = '10'
                else:
                    one.state_2 = '10'
                    one.state_1 = '10'
            else:
                if one.state_1 == '20':
                    if date_ship_residual_time < 30:
                        one.state_2 = '30'
                    else:
                        one.state_2 = '40'
                elif one.state_1 == '30':
                    if plan_invoice_auto_amount != real_invoice_auto_amount:
                        if date_ship_residual_time < 30:
                            one.state_2 = '50'
                        else:
                            one.state_2 = '60'
                    else:
                        one.state_1 = '40'
                        one.state_2 = '70'
                elif one.state_1 == '40':
                        if date_ship_residual_time < 30:
                            one.state_2 = '70'
                            one.state_1 = '40'
                        else:
                            one.state_2 = '75'
                            one.state_1 = '40'
                elif one.state_1 == '50':
                    print('invoice_akiny', len(back_tax_invoice_declare_ids), len(back_tax_invoice_ids))
                    if back_tax_invoice_declare_ids and back_tax_invoice_ids:

                        if len(back_tax_invoice_declare_ids) != len(back_tax_invoice_ids):
                            if date_ship_residual_time >= 30:
                                one.state_2 = '90'
                            else:
                                one.state_2 = '80'
                        else:
                            one.state_1 = '60'
                            one.state_2 = '100'
                    else:
                        if date_ship_residual_time >= 30:
                            one.state_2 = '90'
                        else:
                            one.state_2 = '80'
                elif one.state_1 == '60':
                    if len(back_tax_invoice_residual_0_ids) != 0:
                        if date_ship_residual_time < 45:
                            one.state_2 = '100'
                        else:
                            one.state_2 = '110'
                    else:
                        one.state_1 = '70'
                        one.state_2 = '120'
                else:
                    return True




    def action_lock(self):
        today = datetime.today()
        strptime = datetime.strptime
        lock_date = self.lock_date
        date_ship = self.bill_id.date_ship
        date_ship_residual_time = date_ship and (today - strptime(date_ship, DF)).days or 0
        lock_date_residual_time = lock_date and (today - strptime(lock_date, DF)).days or 0
        plan_invoice_auto_amount = self.plan_invoice_auto_amount
        real_invoice_auto_amount = self.real_invoice_auto_amount
        if plan_invoice_auto_amount != real_invoice_auto_amount:
            if date_ship_residual_time >= 30:
                self.state = '40'
                self.state_1 = '30'
                self.state_2 = '40'
            else:
                self.state = '30'
                self.state_1 = '30'
                self.state_2 = '30'
        else:
            self.state = '50'
            self.state_1 = '40'
            self.state_2 = '70'
        self.lock_date = datetime.today()
        # stage_id = self.bill_id._stage_find(domain=[('code', '=', '013')])
        # self.bill_id.write({
        #     'stage_id': stage_id.id
        # })

    def action_unlock(self):
        today = datetime.today()
        strptime = datetime.strptime
        lock_date = self.lock_date
        date_ship = self.bill_id.date_ship
        date_out_in = self.bill_id.date_out_in

        date_out_in_residual_time = date_out_in and (today - strptime(date_out_in, DF)).days or 0
        if self.state_1 != '30':
            raise Warning('现在状态不可解锁！')
        else:
            self.state_1 = '20'
            if date_out_in_residual_time >= 15:
                self.state_2 = '40'
            else:
                self.state_2 = '30'

    def _action_unlock(self):
        date_ship = self.bill_id.date_ship
        today = datetime.today()
        strptime = datetime.strptime
        date_ship_residual_time = date_ship and (today - strptime(date_ship, DF)).days or 0
        print('date_ship_residual_time_akiny', date_ship_residual_time)
        if self.state in ['30', '40'] and date_ship_residual_time >= 30:
            self.state = '20'
        else:
            self.state = '10'
        self.lock_date = None
        stage_id = self.bill_id._stage_find(domain=[('code', '=', '012')])
        self.bill_id.write({
            'stage_id': stage_id.id
        })

    def action_make_real_in_invoice(self):
        self.state_1 = '50'
        self.compute_state_1_2()

    def open_wizard_tb_po_invoice_new(self):
        self.ensure_one()
        if self.bill_id.locked == False:
            raise Warning('出运合同未锁定,请先锁定出运合同,再进行增加采购的操作!')
        wizard = self.env['wizard.tb.po.invoice.new'].create({
            'tb_id': self.bill_id.id,
                                                          })
        view = self.env.ref('yjzy_extend.wizard_tb_po_form_new')
        line_obj = self.env['wizard.tb.po.invoice.line.new']
        tb_po_expense = self.env['tb.po.invoice'].search([('state','=','25')])
        if tb_po_expense:
            for one in tb_po_expense:
                line_obj.create({
                    'wizard_tb_po_invoice': wizard.id,
                    'tb_po_expense':one.id,
                })

        return {
            'name': _(u'增加采购'),
            'view_type': 'tree,form',
            "view_mode": 'form',
            'res_model': 'wizard.tb.po.invoice.new',
            'type': 'ir.actions.act_window',
            'view_id': view.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': {},
        }



    def compute_state(self):
        for one in self:
            date_ship = one.bill_id.date_ship
            state = one.state
            today = datetime.today()
            strptime = datetime.strptime
            lock_date = one.lock_date
            back_tax_invoice_ids = one.back_tax_invoice_ids
            back_tax_invoice_declare_ids = back_tax_invoice_ids.filtered(lambda x: x.back_tax_declaration_state == '20')
            back_tax_invoice_residual_0_ids = back_tax_invoice_ids.filtered(lambda x: x.residual == 0)

            date_ship_residual_time = date_ship and (today - strptime(date_ship, DF)).days or 0
            lock_date_residual_time = lock_date and (today - strptime(lock_date, DF)).days or 0
            plan_invoice_auto_amount = one.plan_invoice_auto_amount
            real_invoice_auto_amount = one.real_invoice_auto_amount
            print('akiny_date_ship_residual_time', date_ship_residual_time)
            if state == '10' and date_ship_residual_time >= 30:
                one.state = '20'
            if state == '30' and plan_invoice_auto_amount != real_invoice_auto_amount and lock_date_residual_time >= 30:
                one.state = '40'
            if state in ['30', '40'] and plan_invoice_auto_amount == real_invoice_auto_amount:
                one.state = '50'

            if state in ['60', '70', '75', '80', '90']:
                if len(back_tax_invoice_declare_ids) == 0:
                    one.state = '70'
                elif len(back_tax_invoice_declare_ids) == len(back_tax_invoice_ids) == len(
                        back_tax_invoice_residual_0_ids):
                    one.state = '100'
                elif len(back_tax_invoice_declare_ids) == len(back_tax_invoice_ids) != len(
                        back_tax_invoice_residual_0_ids) and len(back_tax_invoice_residual_0_ids) != 0:
                    one.state = '90'
                elif len(back_tax_invoice_declare_ids) == len(back_tax_invoice_ids) and len(
                        back_tax_invoice_residual_0_ids) == 0:
                    one.state = '80'
                elif len(back_tax_invoice_declare_ids) != len(back_tax_invoice_ids):
                    one.state = '75'

#####################################################################################################################
