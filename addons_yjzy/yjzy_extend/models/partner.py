# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning
from ast import literal_eval


class res_partner(models.Model):
    _inherit = 'res.partner'
    _order = "sequence, display_name"

    def compute_amount_purchase_advance(self):
        aml_obj = self.env['account.move.line']
        for one in self:
            lines = aml_obj.search([('company_id', '=', self.env.user.company_id.id), ('partner_id', '=', one.id),
                                    ('account_id.code', '=', '1123')])
            one.advance_currency_id = one.property_purchase_currency_id or one.currency_id
            one.amount_purchase_advance_org = sum(
                [line.get_amount_to_currency(one.advance_currency_id) for line in lines])
            one.amount_purchase_advance = sum([line.get_amount_to_currency(one.currency_id) for line in lines])

    @api.depends('child_contact_ids', 'child_contact_ids.mobile', 'child_contact_ids.phone', 'child_contact_ids.other_social_accounts',
                 'child_contact_ids.comment_contact', 'child_contact_ids.country_id', 'child_contact_ids.name')
    def compute_info(self):
        for one in self:
            for x in one.child_contact_ids:
                if x.phone or x.mobile:
                    phone_mobile = True
                else:
                    phone_mobile = False
                if x.email or x.other_social_accounts:
                    email_social = True
                else:
                    email_social = False
                if not x.name or not x.country_id or not phone_mobile or not email_social or not x.comment_contact:
                    is_child_ids = False
                    one.is_child_ids = is_child_ids
                    break
                else:
                    is_child_ids = True
                    one.is_child_ids = is_child_ids

    @api.depends('sale_order_ids', 'sale_order_ids.approve_date')
    def last_sale_order(self):
        company = self.env.user.company_id.id
        for one in self:
            last_sale_orders = one.sudo().sale_order_ids.filtered(
                lambda x: x.approve_date != False).sorted(lambda x: x.approve_date)
            if last_sale_orders:
                last_order = last_sale_orders[-1]
                one.last_sale_order_approve_date = last_order.approve_date
                print('--lastdate--', last_order, last_order.approve_date)
            else:
                one.last_sale_order_approve_date = False
            # if one.sale_order_ids:
            #     last_order = one.sudo().sale_order_ids[0]
            #     one.last_sale_order_approve_date = last_order.approve_date
            #     print('--lastdate--', last_order, last_order.approve_date)

    # 增加地址翻译
    @api.depends('advance_payment_ids', 'advance_payment_ids.amount', 'advance_payment_ids.advance_total',
                 'advance_payment_ids.advance_balance_total', 'invoice_ids', 'invoice_ids.amount_total',
                 'invoice_ids.residual_signed', 'invoice_ids.amount_total_signed')
    def compute_amount_invoice_advance_payment(self):
        reconcile_ids = self.env['account.reconcile.order.line']
        for one in self:
            invoice = one.invoice_ids  # .filtered(lambda x: x.company_id  == self.env.user.company_id)
            payment = one.advance_payment_ids  # .filtered(lambda x: x.company_id  == self.env.user.company_id)
            # reconcile = reconcile_ids.search([('order_id.partner_id','=',one.id)])
            amount_invoice = sum(x.amount_total_signed for x in invoice)
            amount_residual_invoice = sum(x.residual_signed for x in invoice)
            amount_advance_payment = sum(x.amount for x in payment)
            amount_advance_payment_reconcile = sum(x.advance_total for x in payment)
            # amount_advance_payment_reconcile =  sum(x.amount_advance_org for x in reconcile)
            # amount_residual_advance_payment = amount_advance_payment - amount_advance_payment_reconcile
            amount_residual_advance_payment = sum(x.advance_balance_total for x in payment)
            one.amount_invoice = amount_invoice
            one.amount_residual_invoice = amount_residual_invoice
            one.amount_advance_payment = amount_advance_payment
            one.amount_advance_payment_reconcile = amount_advance_payment_reconcile
            one.amount_residual_advance_payment = amount_residual_advance_payment

            one.amount_invoice_no_store = amount_invoice
            one.amount_residual_invoice_no_store = amount_residual_invoice
            one.amount_advance_payment_no_store = amount_advance_payment
            one.amount_advance_payment_reconcile_no_store = amount_advance_payment_reconcile
            one.amount_residual_advance_payment_no_store = amount_residual_advance_payment

    @api.depends('advance_payment_ids', 'advance_payment_ids.amount', 'supplier_account_reconcile_ids.state',
                 'supplier_account_reconcile_ids.move_ids',
                 'advance_payment_ids.advance_total', 'advance_payment_ids.advance_balance_total',
                 'invoice_ids', 'invoice_ids.amount_total', 'invoice_ids.residual', 'invoice_ids.state',
                 'advance_payment_ids.state', 'supplier_invoice_ids','supplier_invoice_ids',
                 'supplier_invoice_ids.amount_total_signed', 'supplier_invoice_ids.residual_signed',
                 'supplier_advance_payment_ids.amount', 'supplier_advance_payment_ids.advance_total',
                 'supplier_advance_payment_ids.advance_balance_total')
    def compute_supplier_amount_invoice_advance_payment(self):
        reconcile_ids = self.env['account.reconcile.order.line']
        for one in self:
            invoice = one.supplier_invoice_ids  # .filtered(lambda x: x.company_id  == self.env.user.company_id)#等待切换公司能触发执行的动作位置
            payment = one.supplier_advance_payment_ids  # .filtered(lambda x: x.company_id  == self.env.user.company_id)
            # reconcile = reconcile_ids.search([('order_id.partner_id','=',one.id)])
            supplier_amount_invoice = sum(x.amount_total_signed for x in invoice)
            supplier_amount_residual_invoice = sum(x.residual_signed for x in invoice)
            supplier_amount_advance_payment = sum(x.amount for x in payment)
            supplier_amount_advance_payment_reconcile = sum(x.advance_total for x in payment)
            # amount_advance_payment_reconcile =  sum(x.amount_advance_org for x in reconcile)
            # amount_residual_advance_payment = amount_advance_payment - amount_advance_payment_reconcile
            supplier_amount_residual_advance_payment = sum(x.advance_balance_total for x in payment)
            one.supplier_amount_invoice = supplier_amount_invoice
            one.supplier_amount_residual_invoice = supplier_amount_residual_invoice
            one.supplier_amount_advance_payment = supplier_amount_advance_payment
            one.supplier_amount_advance_payment_reconcile = supplier_amount_advance_payment_reconcile
            one.supplier_amount_residual_advance_payment = supplier_amount_residual_advance_payment

            one.supplier_amount_invoice_no_store = supplier_amount_invoice
            one.supplier_amount_residual_invoice_no_store = supplier_amount_residual_invoice
            one.supplier_amount_advance_payment_no_store = supplier_amount_advance_payment
            one.supplier_amount_advance_payment_reconcile_no_store = supplier_amount_advance_payment_reconcile
            one.supplier_amount_residual_advance_payment_no_store = supplier_amount_residual_advance_payment

    @api.depends('sale_order_ids.amount_total', 'sale_order_ids', 'sale_order_ids.state',
                 'sale_order_ids.no_sent_amount_new', 'so_approve_ids',
                 'so_approve_ids.amount_total', 'so_approve_ids.state')
    def compute_sale_order_amount_total(self):
        for one in self:
            so_ids = one.so_approve_ids  # .filtered(lambda x: x.company_id  == self.env.user.company_id)
            so_no_sent_ids = one.sale_order_ids.filtered(
                lambda x: x.no_sent_amount_new != 0 and x.state in ['approve', 'sale', 'done', 'abnormal', 'verifying',
                                                                    'verification'])
            print('tet', so_ids, so_no_sent_ids)
            amount_total = sum(x.amount_total for x in so_ids)

            no_sent_amount = sum(x.no_sent_amount for x in so_no_sent_ids)
            one.sale_order_amount_total = amount_total
            one.so_no_sent_amount = no_sent_amount
            # one.sale_order_amount_total_no_store = amount_total
            # one.so_no_sent_amount_no_store = no_sent_amount

    @api.depends('tb_approve_ids', 'tb_approve_ids.org_sale_amount_new')
    def compute_tb_approve_amount_total(self):
        for one in self:
            tb_ids = one.tb_approve_ids  # .filtered(lambda x: x.company_id  == self.env.user.company_id)
            amount_total = sum(x.org_sale_amount for x in tb_ids)
            print('amount_total', amount_total)
            # one.tb_approve_amount_total = amount_total
            one.tb_approve_amount_total_no_store = amount_total

    @api.depends('payment_ids', 'payment_ids.amount')
    def compute_payment_amount_total(self):
        for one in self:
            payment_ids = one.payment_ids
            payment_amount_total = sum(x.amount for x in payment_ids)
            one.payment_amount_total = payment_amount_total

    @api.depends('po_approve_ids', 'po_approve_ids.purchaser_date', 'po_approve_ids.amount_total',
                 'po_approve_ids.state')
    def compute_po_amount_total(self):
        for one in self:
            po_approve_ids = one.po_approve_ids  # .filtered(lambda x: x.company_id  == self.env.user.company_id)
            po_amount_total = sum(x.amount_total for x in po_approve_ids)
            one.po_amount_total = po_amount_total

            one.po_amount_total_no_store = po_amount_total

    @api.depends('po_purchase_ids.no_deliver_amount_new', 'po_purchase_ids', 'po_purchase_ids.state', 'po_purchase_ids.stage_id',
                 'po_purchase_ids.amount_total',)
    def compute_po_no_sent_amount_total(self):
        for one in self:
            po_purchase_ids = one.po_purchase_ids
            po_no_sent_amount_total = sum(x.no_deliver_amount_new for x in po_purchase_ids)
            one.po_no_sent_amount_total = po_no_sent_amount_total
            one.po_no_sent_amount_total_no_store = po_no_sent_amount_total

    @api.depends('po_tb_line_ids', 'po_tb_line_ids.purchase_cost_new', 'po_tb_line_ids.bill_id.state')
    def compute_tb_approve_po_amount_total(self):
        for one in self:
            po_tb_line_ids = one.po_tb_line_ids  # .filtered(lambda x: x.company_id  == self.env.user.company_id)
            tb_approve_po_amount_total = sum(x.purchase_cost for x in po_tb_line_ids)
            print('tb_approve_po_amount_total', tb_approve_po_amount_total)
            one.tb_approve_po_amount_total = tb_approve_po_amount_total
            one.tb_approve_po_amount_total_no_store = tb_approve_po_amount_total

    # @api.depends('invoice_open_ids', 'invoice_open_ids.state')
    def compute_invoice_open_ids_count(self):
        for one in self:
            one.invoice_open_ids_count = len(one.invoice_open_ids)


    def compute_supplier_invoice_open_ids_count(self):
        for one in self:
            one.supplier_invoice_open_ids_count = len(one.supplier_invoice_ids)

    @api.depends('supplier_invoice_ids', 'supplier_invoice_ids.amount_payment_approval_all',
                 'supplier_invoice_ids.state')
    def compute_supplier_amount_invoice_approval(self):
        for one in self:
            supplier_amount_invoice_approval = sum(x.amount_payment_approval_all for x in one.supplier_invoice_ids)
            one.supplier_amount_invoice_approval = supplier_amount_invoice_approval

    @api.depends('supplier_invoice_ids', 'supplier_invoice_ids.amount_payment_approve_all')
    def compute_supplier_amount_invoice_approve(self):
        for one in self:
            supplier_amount_invoice_approve = sum(x.amount_payment_approve_all for x in one.supplier_invoice_ids)
            one.supplier_amount_invoice_approve = supplier_amount_invoice_approve

    @api.depends('supplier_advance_payment_ids',
                 'supplier_advance_payment_ids.advance_amount_reconcile_order_line_approval')
    def compute_supplier_advance_amount_hxd_line_approval(self):
        for one in self:
            supplier_advance_amount_hxd_line_approval = sum(
                x.advance_amount_reconcile_order_line_approval for x in one.supplier_advance_payment_ids)
            one.supplier_advance_amount_hxd_line_approval = supplier_advance_amount_hxd_line_approval

    @api.depends('so_no_sent_ids')
    def compute_so_no_sent_ids_count(self):
        for one in self:
            so_no_sent_ids_count = len('self.so_no_sent_ids')
            one.so_no_sent_amount = so_no_sent_ids_count

    def compute_display_name(self):
        diff = dict(show_address=None, show_address_only=None, show_email=None)
        names = dict(self.with_context(**diff).name_get())
        for partner in self:
            partner.display_name = names.get(partner.id)

    account_move_line_com = fields.One2many('account.move.line.com', 'partner_id', '日志')

    qingguan_precision = fields.Integer('清关资料打印小数位数')
    # 增加供应商和客户的独立编号，审批完成后添加
    customer_code = fields.Char('客户编码')
    supplier_code = fields.Char('供应商编码')
    # 1102
    # 取采购订单
    po_approve_ids = fields.One2many('purchase.order', 'partner_id', '今年采购合同',
                                     domain=[('purchaser_date', '!=', False),
                                             ('purchaser_date', '>',
                                              fields.datetime.now().strftime('%Y-01-01 00:00:00')),
                                             ('state', 'in',
                                              ['to approve', 'purchase'])])
    po_purchase_ids = fields.One2many('purchase.order', 'partner_id', '所有采购合同',
                                      domain=[('state', 'in', ['purchase', 'to approve'])])
    # 出运合同明细，先创建明细的供应商字段，来自批次号
    po_tb_line_ids = fields.One2many('transport.bill.line', 'supplier_id', '今年出运合同明细',
                                     domain=[('bill_id.approve_date', '!=', False),
                                             ('bill_id.approve_date', '>',
                                              fields.datetime.now().strftime('%Y-01-01 00:00:00')),
                                             ('bill_id.state', 'in',
                                              ['approve', 'confirmed', 'delivered', 'invoiced', 'locked', 'verifying',
                                               'done', 'paid'])])

    po_amount_total = fields.Float('今年审批完成采购金额')  # , compute=compute_po_amount_total, store=True
    po_no_sent_amount_total = fields.Float('未发货余额')  # compute=compute_po_no_sent_amount_total, store=True
    po_amount_total_no_store = fields.Float('今年审批完成采购金额')  # , compute=compute_po_amount_total, store=True
    po_no_sent_amount_total_no_store = fields.Float('未发货余额')  # compute=compute_po_no_sent_amount_total, store=True
    tb_approve_po_amount_total = fields.Float('今年审批完成出运采购金额')  # compute=compute_tb_approve_po_amount_total, store=True
    tb_approve_po_amount_total_no_store = fields.Float('今年审批完成出运采购金额')  # , compute=compute_tb_approve_po_amount_total,store=True
    # 新增

    invoice_ids = fields.One2many('account.invoice', 'partner_id', '应收账单',
                                  domain=[('type', '=', 'out_invoice'),
                                          ('state', 'not in', ['draft', 'cancel'])])
    invoice_open_ids = fields.One2many('account.invoice', 'partner_id', '有余额应收账单',
                                       domain=[('type', '=', 'out_invoice'),
                                               ('state', 'in', ['open'])])
    invoice_open_ids_count = fields.Integer('有余额应收账单数量', compute=compute_invoice_open_ids_count)

    supplier_invoice_ids = fields.One2many('account.invoice', 'partner_id', '应付账单',
                                           domain=[('type', '=', 'in_invoice'),
                                                   ('state', 'not in', ['draft', 'cancel'])])

    supplier_invoice_open_ids_count = fields.Integer('有余额应付账单数量', compute=compute_supplier_invoice_open_ids_count)
    advance_payment_ids = fields.One2many('account.payment', 'partner_id', '预收认领',
                                          domain=[('sfk_type', '=', 'ysrld'),
                                                  ('state', 'in', ['posted', 'reconciled'])],
                                          )
    supplier_advance_payment_ids = fields.One2many('account.payment', 'partner_id', '预付认领',
                                                   domain=[('sfk_type', '=', 'yfsqd'),
                                                           ('state', 'in', ['posted', 'reconciled'])],
                                                   )
    payment_ids = fields.One2many('account.payment', 'partner_confirm_id', '收款流水',
                                  domain=[('sfk_type', '=', 'rcskd'),
                                          ('state', 'in', ['posted', 'reconciled'])],
                                  )
    supplier_payment_ids = fields.One2many('account.payment', 'partner_confirm_id', '付款流水',
                                           domain=[('sfk_type', '=', 'rcfkd'),
                                                   ('state', 'in', ['posted', 'reconciled'])])

    tb_approve_ids = fields.One2many('transport.bill', 'partner_id', '今年出运合同',
                                     domain=[('approve_date', '!=', False),
                                             ('approve_date', '>', fields.datetime.now().strftime('%Y-01-01 00:00:00')),
                                             ('state', 'in',
                                              ['approve', 'confirmed', 'delivered', 'invoiced', 'locked', 'verifying',
                                               'done', 'paid'])])
    so_approve_ids = fields.One2many('sale.order', 'partner_id', '今年销售合同',
                                     domain=[('approve_date', '!=', False),
                                             ('approve_date', '>', fields.datetime.now().strftime('%Y-01-01 00:00:00')),
                                             ('state', 'in',
                                              ['approve', 'sale', 'done', 'abnormal', 'verifying', 'verification'])])
    so_no_sent_ids = fields.One2many('sale.order', 'partner_id', '未完成发货的',
                                     domain=['|', ('no_sent_amount_new', '!=', 0),
                                             ('state_1', 'in',
                                              ['draft', 'submit', 'sales_approve', 'manager_approval', 'approve'])])
    so_no_sent_ids_count = fields.Integer('未完成发货的销售单数量', compute='compute_so_no_sent_ids_count', store=True)

    account_reconcile_ids = fields.One2many('account.reconcile.order', 'partner_id', '应收认领',
                                            domain=[('sfk_type', '=', 'yshxd'), ('state', '=', 'done'),
                                                    ('amount_payment_org', '!=', 0)])
    # account_reconcile_have_sopo_ids = fields.One2many('account.reconcile.order', 'partner_id', '应收认领',
    #                                         domain=[('sfk_type', '=', 'yshxd'), ('state', '=', 'done'),('no_sopo','!=',True),
    #                                                 ('amount_payment_org', '!=', 0)])
    supplier_account_reconcile_ids = fields.One2many('account.reconcile.order', 'partner_id', '应付认领',
                                                     domain=[('sfk_type', '=', 'yfhxd'), ('state', '=', 'done'),
                                                             ('amount_payment_org', '!=', 0)])
    # supplier_account_reconcile_have_sopo_ids = fields.One2many('account.reconcile.order', 'partner_id', '应付认领',
    #                                                  domain=[('sfk_type', '=', 'yfhxd'), ('state', '=', 'done'),('no_sopo','!=',True),
    #                                                          ('amount_payment_org', '!=', 0)])
    amount_invoice = fields.Float(u'应收账单总金额')  # compute='compute_amount_invoice_advance_payment', store=True
    amount_residual_invoice = fields.Float(u'应收款余额')  # compute='compute_amount_invoice_advance_payment', store=True
    amount_advance_payment = fields.Float('u预收总金额')  # compute='compute_amount_invoice_advance_payment', store=True
    amount_residual_advance_payment = fields.Float('预收余额')  # compute='compute_amount_invoice_advance_payment', store=True
    amount_advance_payment_reconcile = fields.Float('预收认领金额')  # compute='compute_amount_invoice_advance_payment', store=True

    amount_invoice_no_store = fields.Float(u'应收账单总金额')  # compute='compute_amount_invoice_advance_payment',store=True
    amount_residual_invoice_no_store = fields.Float(u'应收款余额')  # compute='compute_amount_invoice_advance_payment',store=True
    amount_advance_payment_no_store = fields.Float('u预收总金额')  # compute='compute_amount_invoice_advance_payment',store=True
    amount_residual_advance_payment_no_store = fields.Float('预收余额')  # compute='compute_amount_invoice_advance_payment',store=True
    amount_advance_payment_reconcile_no_store = fields.Float('预收认领金额')  # compute='compute_amount_invoice_advance_payment',store=True

    sale_order_amount_total = fields.Float('今年审批完成销售金额', )  # compute=compute_sale_order_amount_total, store=True
    so_no_sent_amount = fields.Float('未发货余额')  # , compute=compute_sale_order_amount_total, store=True

    sale_order_amount_total_no_store = fields.Float('今年审批完成销售金额')  # ,compute=compute_sale_order_amount_total, store=True
    so_no_sent_amount_no_store = fields.Float('未发货余额')  # , compute=compute_sale_order_amount_total, store=True
    tb_approve_amount_total = fields.Float('今年审批完成出运金额')  # compute=compute_tb_approve_amount_total, store=True
    tb_approve_amount_total_no_store = fields.Float('今年审批完成出运金额', )  # compute=compute_tb_approve_amount_total, store=True

    payment_amount_total = fields.Float('收款总金额', compute=compute_payment_amount_total, store=True)
    supplier_amount_invoice = fields.Float(u'应付账单总金额', compute=compute_supplier_amount_invoice_advance_payment,
                                           store=True)
    supplier_amount_residual_invoice = fields.Float(u'应付款余额', compute=compute_supplier_amount_invoice_advance_payment,
                                                    store=True)
    supplier_amount_invoice_approval = fields.Float(u'已申请未审批', compute=compute_supplier_amount_invoice_approval,
                                                    store=True)
    supplier_amount_invoice_approve = fields.Float(u'已审批未付款', compute=compute_supplier_amount_invoice_approve,
                                                   store=True)
    supplier_amount_advance_payment = fields.Float('u预付总金额', compute=compute_supplier_amount_invoice_advance_payment,
                                                   store=True)
    supplier_amount_residual_advance_payment = fields.Float('预付余额',
                                                            compute=compute_supplier_amount_invoice_advance_payment,
                                                            store=True)
    supplier_amount_advance_payment_reconcile = fields.Float('预付认领金额',
                                                             compute=compute_supplier_amount_invoice_advance_payment,
                                                             store=True)
    supplier_advance_amount_hxd_line_approval = fields.Float('审批中预付',
                                                             compute=compute_supplier_advance_amount_hxd_line_approval,
                                                             store=True)

    supplier_payment_amount_total = fields.Float('付款总金额', compute=compute_payment_amount_total, store=True)

    supplier_amount_invoice_no_store = fields.Float(u'应付账单总金额', compute=compute_supplier_amount_invoice_advance_payment, store=True)
    supplier_amount_residual_invoice_no_store = fields.Float(u'应付款余额',
                                                             compute=compute_supplier_amount_invoice_advance_payment,
                                                             store=True)

    supplier_amount_advance_payment_no_store = fields.Float('u预付总金额',
                                                            compute=compute_supplier_amount_invoice_advance_payment,
                                                            store=True)
    supplier_amount_residual_advance_payment_no_store = fields.Float('预付余额',
                                                                     compute=compute_supplier_amount_invoice_advance_payment,
                                                                     store=True)
    supplier_amount_advance_payment_reconcile_no_store = fields.Float('预付认领金额',
                                                                      compute=compute_supplier_amount_invoice_advance_payment,
                                                                      store=True)

    # 不要了

    mark_ids = fields.Many2many('transport.mark', 'ref_mark_patner', 'pid', 'mid', u'唛头')
    mark_comb_ids = fields.Many2many('mark.comb', 'ref_comb_partner', 'pid', 'cid', u'唛头组')
    exchange_type_ids = fields.Many2many('exchange.type', 'ref_exchange_partner', 'pid', 'eid', u'交单方式')
    exchange_demand_ids = fields.One2many('exchange.demand', 'partner_id', u'交单要求')
    demand_info = fields.Text(u'交单要求')
    wechat = fields.Char(u'微信')
    qq = fields.Char(u'QQ')
    skype = fields.Char('Skype')
    auto_yfsqd = fields.Boolean(u'自动生成预付')
    jituan_name = fields.Char(u'集团名称')
    campaign_id = fields.Many2one('utm.campaign', u'客户来源')
    is_required = fields.Boolean(u'检查必填', default=False)
    level = fields.Selection([(x, x.upper()) for x in 'abcde'], u'客户等级')
    street = fields.Char(translate=True)
    street2 = fields.Char(translate=True)
    city = fields.Char(translate=True)
    code = fields.Char('编码')  # 13.0用ref替代
    product_manager_id = fields.Many2one('res.users', related='user_id.product_manager_id', store=True)
    type = fields.Selection(selection_add=[('notice', u'发货代理')])
    type1 = fields.Selection(
        [('contact', u'联系人'),
         ('invoice', u'发票主体'),
         ('delivery', u'收货地址'),
         ], string='Address Type',
        default='contact',
        help="Used to select automatically the right address according to the context in sales and purchases documents.")
    # mark_comb_id = fields.Many2one('mark.comb',u'唛头')
    customer_purchase_in_china_currency_id = fields.Many2one('res.currency', '客户在中国采购规模币种', default=lambda
        self: self.env.user.company_id.currency_id.id)
    customer_sale_total_currency_id = fields.Many2one('res.currency', '客户销售额币种',
                                                      default=lambda self: self.env.user.company_id.currency_id.id)
    supplier_sale_total_currency_id = fields.Many2one('res.currency', '供应商销售额币种', default=lambda
        self: self.env.user.company_id.currency_id.id)
    supplier_export_total_currency_id = fields.Many2one('res.currency', '供应商出口额币种', default=lambda
        self: self.env.user.company_id.currency_id.id)
    mark_html = fields.Html('唛头')
    payee1 = fields.Char('收款人')
    payee1_address = fields.Text('收款人地址')
    account1 = fields.Char('账户')
    swift1 = fields.Char('SWIFT(非中国大陆供应商)')
    bank1 = fields.Char('银行')
    bank1_address = fields.Char('银行地址')
    other_attachment = fields.Many2many('ir.attachment', string='其他补充资料附件')

    manager_ids = fields.Many2many('res.users', 'm_id', 'ru_id', 'p_id', '总经理')
    salesman_ids = fields.Many2many('res.users', 'm_1_id', 'ru_1_id', 'p_1_id', '业务负责人')
    sales_assistant_ids = fields.Many2many('res.users', 'm_2_id', 'ru_2_id', 'p_2_id', '销售助理')
    purchase_assistant_ids = fields.Many2many('res.users', 'm_3_id', 'ru_3_id', 'p_3_id', '采购助理')

    partner_name_used_ids = fields.One2many('partner.name.used', 'partner_id', '曾用名')

    # @api.depends('salesman_ids','sales_assistant_ids')
    # def compute_user_id(self):
    #     for one in self:
    #         salesman_ids = one.salesman_ids
    #         sales_assistant_ids = one.sales_assistant_ids
    #         if salesman_ids:
    #             if len(salesman_ids) == 1:
    #                 one.user_id = salesman_ids
    #             else:
    #                 one.user_id = salesman_ids[0]
    #         else:
    #             one.user_id = None
    #         if sales_assistant_ids:
    #             if len(sales_assistant_ids) == 1:
    #                 one.assistant_id = sales_assistant_ids
    #             else:
    #                 one.assistant_id = sales_assistant_ids[0]
    #         else:
    #             one.assistant_id = None

    user_id = fields.Many2one('res.users', string='Salesperson',
                              help='The internal user that is in charge of communicating with this contact if any.')  # compute=compute_user_id, store=True,

    # 13已经添加
    assistant_id = fields.Many2one('res.users', )  # compute=compute_user_id,store=True

    jituan_id = fields.Many2one('ji.tuan', '集团')
    comment_contact = fields.Text(u'对接内容描述')
    devloper_id = fields.Many2one('res.partner', u'开发人员',
                                  domain=[('is_inter_partner', '=', True), ('company_type', '=', 'personal')])
    full_name = fields.Char('公司全称', track_visibility='onchange')
    name = fields.Char(index=True, track_visibility='onchange')
    full_name_1 = fields.Char('公司全称')
    name_1 = fields.Char('Name')
    wharf_src_id = fields.Many2one('stock.wharf', u'装船港')
    wharf_dest_id = fields.Many2one('stock.wharf', u'目的港')
    term_description = fields.Html(u'销售条款')  # 13改成term_sale
    term_purchase = fields.Html(u'采购条款')
    need_purchase_fandian = fields.Boolean(u'采购返点')
    purchase_fandian_ratio = fields.Float(u'返点比例：%')
    purchase_fandian_partner_id = fields.Many2one('res.partner', u'返点对象')
    is_inter_partner = fields.Boolean(u'是否内部', default=False)

    notice_man = fields.Text(u'通知人')
    delivery_man = fields.Text(u'收货人')

    contract_type = fields.Selection([('a', '模式1'), ('b', '模式2'), ('c', '模式3')], '合同类型', default='c')
    gongsi_id = fields.Many2one('gongsi', '销售主体')
    purchase_gongsi_id = fields.Many2one('gongsi', '采购主体')
    sale_currency_id = fields.Many2one('res.currency', '销售币种')
    customer_product_ids = fields.One2many('product.product', 'customer_id', '客户采购产品')
    child_delivery_ids = fields.One2many('res.partner', 'parent_id',
                                         domain=[('type', '=', 'delivery'), ('active', '=', True)], string='收货地址')
    child_contact_ids = fields.One2many('res.partner', 'parent_id',
                                        domain=[('type', '=', 'contact'), ('active', '=', True)], string='联系人')
    child_invoice_ids = fields.One2many('res.partner', 'parent_id',
                                        domain=[('type', '=', 'invoice'), ('active', '=', True)], string='发票主体')
    fax = fields.Char(u'传真')
    partner_source_id = fields.Many2one('partner.source', u'来源')  # 需要关联模块
    customer_info_from_uid = fields.Many2one('res.partner', u'客户获取人', domain=[('is_inter_partner', '=', True),
                                                                              ('company_type', '=', 'personal')])
    is_child_ids = fields.Boolean(u'检查联系人字段', default=False, compute=compute_info)
    sequence = fields.Integer(u'排序', default=10, index=True)
    customer_purchase_in_china = fields.Char(u'客户在中国采购规模(CNY)')
    customer_purchase_in_china_note = fields.Text(u'备注')
    customer_sale_total = fields.Char(u'客户销售额(CNY)')
    customer_sale_total_note = fields.Text(u'备注')
    supplier_sale_total = fields.Char(u'供应商销售额(CNY)')
    supplier_sale_total_note = fields.Text(u'备注')
    supplier_export_total = fields.Char(u'供应商出口额(CNY)')
    supplier_export_total_note = fields.Text(u'备注')
    # akiny
    customer_product_origin_ids = fields.One2many('partner.product.origin', 'partner_id', u'客户产品')  # 关联客户产品模型
    address_text = fields.Text(u'地址')

    mark_text = fields.Text(u'唛头')
    city_product_origin = fields.Char('产地')

    supplier_info_from_uid = fields.Many2one('res.partner', u'供应商获取人', domain=[('is_inter_partner', '=', True),
                                                                               ('company_type', '=', 'personal')])
    attachment_business_license = fields.Many2many('ir.attachment', string='营业执照以及其他资料附件')
    actual_controlling_person = fields.Char(u'实际控股人')

    partner_hs = fields.Many2many('hs.hs', string='产品品名')
    other_social_accounts = fields.Char(u'社交帐号')
    partner_level = fields.Many2one('partner.level', '等级')
    is_editable = fields.Boolean(u'是否允许编辑')

    former_name = fields.Char(u'曾用名')
    can_not_be_deleted = fields.Boolean(u'不允许删除', default=False, readonly=True)
    birthday = fields.Date(u'生日')

    sales_approve_uid = fields.Many2one('res.users', '审批责任人')
    sales_approve_date = fields.Date('责任人审批日期')
    approve_uid = fields.Many2one('res.users', '审批合规')
    approve_date = fields.Date('合规审批日期')
    done_uid = fields.Many2one('res.users', '审批总经理')
    done_date = fields.Date('总经理审批日期')
    last_sale_order_approve_date = fields.Date(u'最近一次下单', compute='last_sale_order',store=True)
    invoice_title = fields.Char(u'发票抬头')

    # 暂时未添加
    state = fields.Selection([('draft', u'草稿'),
                              ('check', u'提交前必填项检查'),
                              ('submit', u'已提交'),
                              ('to approve', u'责任人已审批'),
                              ('approve', u'合规审批完成'), ('done', u'完成'), ('refuse', u'拒绝'), ('cancel', u'取消')],
                             string=u'状态', index=True, track_visibility='onchange', default='draft')
    advance_currency_id = fields.Many2one('res.currency', compute=compute_amount_purchase_advance,
                                          string=u'外币')  # 后期需要优化，分币种统计，根据分录的币种统计
    amount_purchase_advance_org = fields.Monetary('预付金额:外币', currency_field='advance_currency_id',
                                                  compute=compute_amount_purchase_advance)
    amount_purchase_advance = fields.Monetary('预付金额:本币', currency_field='currency_id',
                                              compute=compute_amount_purchase_advance)
    is_ok = fields.Boolean('是否有效', default=True)

    # 14.0————————————
    contract_suffix = fields.Char('合同后缀')

    def button_compute_display_name(self):
        for one in self:
            one._compute_display_name()

    # def write(self, vals):
    #     res = super(res_partner, self).write(vals)
    #
    #     if ('contract_suffix' in vals):
    #         contract_suffix_1 = self.contract_suffix.replace(' ','')
    #         self.write({'contract_suffix':contract_suffix_1,})
    #     return res

    @api.constrains('contract_suffix')
    def check_name(self):
        for one in self:
            if one.contract_suffix == False:
                break
            else:
                if self.search_count([('contract_suffix', '=', one.contract_suffix)]) > 1:
                    raise Warning('合同后缀重复')

    # 审批完成的时候添加客户和供应商编号
    def approve_create_code(self):
        seq_obj = self.env['ir.sequence']
        for one in self:
            if one.customer_code: continue
            if one.supplier_code: continue
            if one.customer and one.is_company == True:
                one.customer_code = seq_obj.next_by_code('res.partner.customer.new')
            elif one.supplier and one.is_company == True:
                one.supplier_code = seq_obj.next_by_code('res.partner.supplier.new')
            else:
                pass

        return True

    @api.constrains('name')
    def check_name(self):
        for one in self:
            if one.name == False:
                break
            else:
                if self.search_count([('name', '=', one.name)]) > 1:
                    raise Warning('客户简称重复')

    @api.constrains('full_name')
    def check_full_name(self):
        for one in self:
            if one.full_name == False:
                break
            else:
                if self.search_count([('full_name', '=', one.full_name)]) > 1:
                    raise Warning('客户全称重复')

    @api.multi
    def toggle_active_partner(self):
        """ Inverse the value of the field ``active`` on the records in ``self``. """

        for record in self:
            record.active = not record.active
            for one in record.child_ids:
                one.active = not one.active

    def action_view_partner_invoices_new(self):
        form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.invoice_new_tree')
        self.ensure_one()
        return {
            'name': u'客户应收',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('partner_id', 'in', [self.id]), ('yjzy_type', '=', 'sale'), ('type', '=', 'out_invoice'),
                       ('state', 'in', ['paid', 'open'])],
            'target': 'new'
        }

    def action_view_partner_supplier_invoices(self):
        form_view = self.env.ref('yjzy_extend.view_account_supplier_invoice_new_form')
        tree_view = self.env.ref('account.invoice_supplier_tree')
        self.ensure_one()
        return {
            'name': u'供应商应付',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('partner_id', 'in', [self.id]), ('yjzy_type', '=', 'purchase'), ('type', '=', 'in_invoice'),
                       ('state', 'in', ['paid', 'open'])],
            'target': 'new'
        }

    @api.multi
    def print_invoice_payment(self):
        if self.customer == True and not self.invoice_ids and not self.advance_payment_ids:
            raise Warning('没有可以打印的')
        if self.supplier == True and not self.supplier_invoice_ids and not self.supplier_advance_payment_ids:
            raise Warning('没有可以打印的')
        return self.env.ref('yjzy_extend.action_report_partner_invoice_payment').report_action(self)

    def open_sale_order(self):
        # form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.new_sale_order_advance_tree')
        self.ensure_one()
        return {
            'name': u'销售合同对应预收',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree')],
            'domain': [('partner_id', 'in', [self.id]), ('yjzy_payment_ids', '!=', False)],
            'target': 'new'
        }

    def open_reconcile_order_line(self):
        # form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.account_yshxd_line_tree_view')
        self.ensure_one()
        for one in self:
            return {
                'name': u'预收认领',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.reconcile.order.line',
                'type': 'ir.actions.act_window',
                'views': [(tree_view.id, 'tree')],
                'domain': [('order_id.partner_id', 'in', [self.id]), ('order_id.state', '=', 'done'),
                           ('amount_advance_org', '!=', 0)],
                'context': {'group_by': 'yjzy_payment_display_name', 'default_sfk_type': 'yshxd', },
                'target': 'new'

            }

    def open_reconcile_order_line_invoice(self):
        # form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.account_yshxd_line_tree_view')
        self.ensure_one()
        for one in self:
            return {
                'name': u'应收认领明细',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.reconcile.order.line',
                'type': 'ir.actions.act_window',
                'views': [(tree_view.id, 'tree')],
                'domain': [('order_id.partner_id', 'in', [self.id]), ('order_id.state', '=', 'done'),
                           ('amount_total_org', '!=', 0)],
                'context': {'group_by': 'invoice_display_name', 'default_sfk_type': 'yshxd'},
                'target': 'new'

            }

    def open_sale_order_approve(self):
        # form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.new_sale_order_approve_tree')
        self.ensure_one()
        return {
            'name': u'销售合同',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree')],
            'domain': [('partner_id', 'in', [self.id]),
                       ('state', 'in', ['approve', 'sale', 'done', 'abnormal', 'verifying', 'verification'])],
            'context': {'group_by': 'approve_date:year', 'same_customer': 1},
            'target': 'new'
        }

    def open_sale_order_no_sent(self):
        # form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.new_sale_order_approve_tree')
        self.ensure_one()
        return {
            'name': u'销售合同',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree')],
            'domain': [('partner_id', 'in', [self.id]), ('no_sent_amount_new', '!=', 0),
                       ('state', 'in', ['approve', 'sale', 'done', 'abnormal', 'verifying', 'verification'])],
            'context': {'group_by': 'approve_date:year', 'same_customer': 1},
            'target': 'new'
        }

    def open_tb_approve(self):
        # form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.view_transport_bill_tenyale_sales_tree')
        self.ensure_one()
        return {
            'name': u'出运合同',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'transport.bill',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree')],
            'domain': [('partner_id', 'in', [self.id]), (
            'state', 'in', ['approve', 'confirmed', 'delivered', 'invoiced', 'locked', 'verifying', 'done', 'paid'])],
            'context': {'group_by': 'approve_date:year', 'same_customer': 1},
            'target': 'new'
        }

    def open_advance(self):
        form_view = self.env.ref('yjzy_extend.view_ysrld_advance_form')
        tree_view = self.env.ref('yjzy_extend.view_ysrld_reconcile_tree_1')
        self.ensure_one()
        return {
            'name': u'预收列表',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('partner_id', 'in', [self.id]), ('sfk_type', '=', 'ysrld'),
                       ('state', 'in', ['posted', 'reconciled'])],
            'target': 'new'
        }

    def open_supplier_advance(self):
        form_view = self.env.ref('yjzy_extend.view_yfsqd_form')
        tree_view = self.env.ref('yjzy_extend.view_yfsqd_account_tree')
        self.ensure_one()
        return {
            'name': u'预收列表',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('partner_id', 'in', [self.id]), ('sfk_type', '=', 'yfsqd'),
                       ('state', 'in', ['posted', 'reconciled'])],
            'target': 'new'
        }

        # self.ensure_one()
        # action = self.env.ref('yjzy_extend.action_sale_account_invoice_new').read()[0]
        # action['domain'] = literal_eval(action['domain'])
        # action['domain'].append(('partner_id', 'child_of', self.id))
        # return action

    # 13已经添加
    @api.onchange('invoice_title')
    def onchange_invoice_title(self):
        if self.type == 'delivery':
            self.name = self.invoice_title

    @api.model
    def create(self, vals):
        one = super(res_partner, self).create(vals)
        if one.customer and one.company_type == 'company':
            one.create_my_pricelist()  # 这个方法还没有
        one.generate_code()  # 这个已经用ref替换

        return one

    def generate_code(self):
        seq_obj = self.env['ir.sequence']
        for one in self:
            if one.code: continue
            seq_code = None
            if one.customer and one.supplier:
                seq_code = 'res.partner.both'
            elif one.customer:
                seq_code = 'res.partner.customer'
            elif one.supplier:
                seq_code = 'res.partner.supplier'
            else:
                pass

            if seq_code:
                one.code = seq_obj.next_by_code(seq_code)

        return True

    @api.onchange('sale_currency_id')
    def onchange_sale_currency(self):
        if self.sale_currency_id:
            pricelist = self.env['product.pricelist'].search(
                [('customer_id', '=', self._origin.id), ('currency_id', '=', self.sale_currency_id.id)], limit=1)

            print('====', pricelist, [('customer_id', '=', self.id), ('currency_id', '=', self.sale_currency_id.id)])

            if pricelist:
                self.property_product_pricelist = pricelist

    def create_my_pricelist(self):
        p_obj = self.env['product.pricelist']
        for one in self:
            # pricelist = p_obj.create({
            #     'name': one.name,
            #     'customer_id': one.id,
            #     'currency_id':  self.sale_currency_id.id or self.env.user.company_id.currency_id.id,
            #     'type': 'special',
            # })

            currency_cny = self.env['res.currency'].search([('name', '=', 'CNY')], limit=1)
            currency_usd = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)

            pricelist_cny = p_obj.create({
                'name': one.name,
                'customer_id': one.id,
                'currency_id': currency_cny.id,
                'type': 'special',
            })
            pricelist_usd = p_obj.create({
                'name': one.name,
                'customer_id': one.id,
                'currency_id': currency_usd.id,
                'type': 'special',
            })

            one.property_product_pricelist = pricelist_cny

            property_record_cny = self.env['ir.property'].search([
                ('name', '=', 'property_product_pricelist'),
                ('res_id', '=', 'res.partner,%s' % one.id),
                ('fields_id.name', '=', 'property_product_pricelist'),
                ('value_reference', '=', 'product.pricelist,%s' % pricelist_cny.id)])

            print('====', property_record_cny)
            property_record_cny.company_id = False

            one.property_product_pricelist = pricelist_usd

            property_record_usd = self.env['ir.property'].search([
                ('name', '=', 'property_product_pricelist'),
                ('res_id', '=', 'res.partner,%s' % one.id),
                ('fields_id.name', '=', 'property_product_pricelist'),
                ('value_reference', '=', 'product.pricelist,%s' % pricelist_usd.id)])

            print('====', property_record_usd)

            property_record_usd.company_id = False

            if one.sale_currency_id.name == 'USD':
                one.property_product_pricelist = pricelist_usd
            else:
                one.property_product_pricelist = pricelist_cny

    def action_submit(self):
        war = ''
        if self.customer:
            if self.full_name and self.contract_suffix and self.country_id and self.jituan_id and self.sale_currency_id and self.property_payment_term_id and \
                    self.phone and self.fax and self.website and self.address_text and self.contract_type and \
                    self.gongsi_id and self.purchase_gongsi_id and self.partner_source_id and self.customer_info_from_uid and self.devloper_id and \
                    self.customer_purchase_in_china and self.customer_sale_total and \
                    self.self.child_contact_ids and self.customer_product_origin_ids and self.is_child_ids:
                self.state = 'submit'
            else:
                if not self.full_name:
                    war += '客户公司全称不为空\n'
                if not self.country_id:
                    war += '公司所在国不为空\n'
                if not self.jituan_id:
                    war += '所属集团不为空\n'
                if not self.sale_currency_id:
                    war += '销售币种不为空\n'
                if not self.property_payment_term_id:
                    war += '付款条款不为空\n'
                if not self.phone:
                    war += '电话不为空\n'
                if not self.fax:
                    war += '传真不为空\n'
                if not self.website:
                    war += '网址不为空\n'
                if not self.address_text:
                    war += '地址不为空\n'
                if not self.contract_type:
                    war += '模式不为空\n'
                if not self.gongsi_id:
                    war += '销售主体不为空\n'
                if not self.purchase_gongsi_id:
                    war += '采购主体不为空\n'
                if not self.partner_source_id:
                    war += '来源不为空\n'
                if not self.customer_info_from_uid:
                    war += '客户获取人不为空\n'
                if not self.devloper_id:
                    war += '开发者不为空\n'

                if not self.customer_purchase_in_china:
                    war += '客户在中国采购规模不为空\n'
                if not self.customer_sale_total:
                    war += '客户销售额不为空\n'
                if not self.child_contact_ids:
                    war += '联系人信息不能为空\n'

                for x in self.child_contact_ids:
                    if not x.country_id:
                        war += '联系人%s 国家不能为空\n' % x.name
                    if not x.function:
                        war += '联系人%s 工作岗位不能为空\n' % x.name
                    if not x.phone and not x.mobile:
                        war += '联系人%s 电话或者手机不能为空\n' % x.name
                    if not x.email and not x.other_social_accounts:
                        war += '联系人%s 电子邮件或者社交账号不能为空\n' % x.name
                    if not x.comment_contact:
                        war += '联系人%s 对接内容描述不能为空\n' % x.name
                if not self.customer_product_origin_ids:
                    war += '客户经营的产品不能为空\n'
                if war:
                    raise Warning(war)
        if self.supplier:
            if self.full_name and self.country_id and self.city_product_origin and self.jituan_id and self.property_purchase_currency_id and \
                    self.property_supplier_payment_term_id and self.phone and self.fax and self.website and self.address_text and \
                    self.partner_source_id and self.supplier_info_from_uid and self.actual_controlling_person and self.attachment_business_license and \
                    self.supplier_export_total and self.supplier_sale_total and self.bank_ids and self.partner_level and \
                    self.self.child_contact_ids and self.customer_product_origin_ids and self.is_child_ids and self.child_invoice_ids:
                self.state = 'submit'
            else:
                if not self.full_name:
                    war += '客户公司全称不为空\n'
                if not self.country_id:
                    war += '公司所在国不为空\n'
                if not self.city_product_origin:
                    war += '产地不为空\n'
                if not self.jituan_id:
                    war += '所属集团不为空\n'
                if not self.property_purchase_currency_id:
                    war += '币种不为空\n'
                if not self.property_supplier_payment_term_id:
                    war += '付款条款不为空\n'
                if not self.phone:
                    war += '电话不为空\n'
                if not self.fax:
                    war += '传真不为空\n'
                if not self.website:
                    war += '网址不为空\n'
                if not self.address_text:
                    war += '地址不为空\n'
                if not self.partner_level:
                    war += '等级不为空\n'
                if not self.partner_source_id:
                    war += '来源不为空\n'
                if not self.supplier_info_from_uid:
                    war += '供应商获取人不为空\n'
                if not self.contract_suffix:
                    war += '合同后缀不为空\n'
                if not self.supplier_export_total:
                    war += '供应商出口额不为空\n'
                if not self.supplier_sale_total:
                    war += '供应商销售额不为空\n'

                if not self.child_contact_ids:
                    war += '联系人信息不能为空\n'

                for x in self.child_contact_ids:
                    if not x.country_id:
                        war += '联系人%s 国家不能为空\n' % x.name
                    if not x.function:
                        war += '联系人%s 工作岗位不能为空\n' % x.name
                    if not x.phone and not x.mobile:
                        war += '联系人%s 电话或者手机不能为空\n' % x.name
                    if not x.email and not x.other_social_accounts:
                        war += '联系人%s 电子邮件或者社交账号不能为空\n' % x.name

                    if not x.comment_contact:
                        war += '联系人%s 对接内容描述不能为空\n' % x.name
                if not self.actual_controlling_person:
                    war += '实际控股人不能为空\n'
                if not self.attachment_business_license:
                    war += '营业执照及其他资料附件不能为空\n'
                if not self.bank_ids:
                    war += '银行账户信息不能为空\n'
                if not self.customer_product_origin_ids:
                    war += '供应商经营产品不能为空\n'
                if war:
                    raise Warning(war)

    def action_to_approve(self):
        if self.user_id == self.env.user:
            return self.write({'state': 'to approve',
                               'sales_approve_uid': self.env.user.id,
                               'sales_approve_date': fields.datetime.now()})
        else:
            raise Warning(u'必须是责任人才能审批')

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id.code == 'CN':
            self.lang = 'zh_CN'
        else:
            self.lang = 'en_US'

    def action_approve(self):
        return self.write({'state': 'approve',
                           'approve_uid': self.env.user.id,
                           'approve_date': fields.datetime.now()})

    def action_done(self):
        self.approve_create_code()
        if self.can_not_be_deleted == False:
            self.can_not_be_deleted = True
        return self.write({'state': 'done',
                           'done_uid': self.env.user.id,
                           'done_date': fields.datetime.now()})

    def action_refuse(self):
        if self.state == 'submit' and self.user_id != self.env.user and self.customer == True:
            raise Warning(u'责任人审批状态必须是责任人才能拒绝')
        else:
            return self.write({'state': 'refuse'})

    def action_cancel(self):
        # if self.state in ('refuse', 'draft') and self.can_not_be_deleted == False:
        if self.state not in ('refuse', 'draft'):
            raise Warning(u'只有拒绝或者草稿状态才能取消！')
        else:
            return self.write({'state': 'cancel'})

    #   else:
    #
    #     if self.can_not_be_deleted == True:
    #           raise Warning(u'已经审批过的记录不允许删除！请联系总经理！')

    # 准备添加

    def unlink(self):
        user = self.env.user
        for one in self:
            if user.has_group('sales_team.group_manager') or (one.type in ['contact','delivery','invoice'] and one.company_type != 'company'):
                return super(res_partner, self).unlink()
            else:
                if one.create_uid != user:
                    raise Warning(u'只有创建者才允许删除')
                if one.state not in ('refuse', 'draft') and one.is_editable == False:
                    raise Warning(u'只有拒绝或者草稿状态才能删除！')

    # @api.multi
    # def write(self,values):
    #     if values.get('state','') == 'check':
    #        values['is_inter_partner'] = True
    #        return super(res_partner, self).write(values)

    def open_form_view(self):
        return {
            'name': '联系人',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    # @api.multi
    def action_check(self):
        # if self.create_uid == self.env.user:
        self.state = 'check'

        # else:
        #     raise Warning(u'必须是创建人才能提交')

    def action_draft(self):
        partner = self.filtered(lambda s: s.state in ['cancel'])
        # if self.create_uid == self.env.user:
        return self.write({'state': 'draft', })
        # else:
        #     raise Warning(u'必须是创建人才能提交')

    # def unlink(self):
    #    for one in self:
    #        if one.state != 'cancel':
    #           raise Warning('不能删除非取消状态发运单')
    #    return super(res_partner, self).unlink()
    # 看起来应该是用不到的
    def select_products(self):
        if self.flag_order == 'so':
            order_id = self.env['sale.order'].browse(self._context.get('active_id', False))
            for product in self.product_ids:
                self.env['sale.order.line'].create({
                    'product_id': product.id,
                    'product_uom': product.uom_id.id,
                    'price_unit': product.lst_price,
                    'order_id': order_id.id
                })
        elif self.flag_order == 'po':
            order_id = self.env['purchase.order'].browse(self._context.get('active_id', False))
            for product in self.product_ids:
                self.env['purchase.order.line'].create({
                    'product_id': product.id,
                    'name': product.name,
                    'date_planned': order_id.date_planned,
                    'product_uom': product.uom_id.id,
                    'price_unit': product.lst_price,
                    'product_qty': 1.0,
                    'order_id': order_id.id
                })

    @api.onchange('type1')
    def _onchange_type1(self):
        self.type = self.type1

    @api.multi
    def name_get(self):
        res = []
        for partner in self:
            name_1 = partner.partner_name_used_ids and partner.partner_name_used_ids[-1].name_used or ''
            if name_1 != '':
                x_1 = '['
                x_2 = ']'
            else:
                x_1 = ''
                x_2 = ''
            name = "%s%s%s%s" % (partner.name or '', x_1, name_1, x_2)

            if partner.company_name or partner.parent_id:
                if not name and partner.type in ['invoice', 'delivery', 'other']:
                    name = dict(self.fields_get(['type'])['type']['selection'])[partner.type]
                if not partner.is_company:
                    name = "%s, %s" % (partner.commercial_company_name or partner.parent_id.name, name)
            if self._context.get('show_address_only'):
                name = partner._display_address(without_company=True)
            if self._context.get('show_address'):
                name = name + "\n" + partner._display_address(without_company=True)
            name = name.replace('\n\n', '\n')
            name = name.replace('\n\n', '\n')
            if self._context.get('show_email') and partner.email:
                name = "%s <%s>" % (partner.name, partner.email)
                if partner.parent_id:
                    name += ':' + partner.parent_id.name
            if self._context.get('html_format'):
                name = name.replace('\n', '<br/>')
            res.append((partner.id, name))
        return res

    #
    # @api.onchange('name','full_name')
    # def onchange_name(self):
    #     name_used = self.name_1
    #     full_name_used = self.full_name_1
    #     name_used_obj = self.env['partner.name.used']
    #     if self.partner_name_used_ids:
    #         for one in self.partner_name_used_ids:
    #             if name_used == one.name_used and full_name_used == one.full_name_used:
    #                 break
    #             elif name_used == one.name_used and full_name_used != one.full_name_used:
    #                 one.update({
    #                     'full_name_used': full_name_used,
    #                 })
    #             elif name_used != one.name_used and full_name_used == one.full_name_used:
    #                 one.update({
    #                     'name_used': name_used,
    #                 })
    #             else:
    #                 name_used_line = name_used_obj.create({
    #                     'name_used': self.name,
    #                     'full_name_used': self.full_name,
    #                     'partner_id': self.id
    #                 })
    #         self.name_1 = self.name
    #         self.full_name_1 = self.full_name
    #     else:
    #         name_used_line = name_used_obj.create({
    #             'name_used': self.name,
    #             'full_name_used': self.full_name,
    #             'partner_id': self.id
    #         })
    #         self.name_1 = self.name
    #         self.full_name_1 = self.full_name

    # def write(self, vals):
    #     res = super(res_partner, self).write(vals)
    #     name_used = self.name_1
    #     full_name_used = self.full_name_1
    #     name_used_obj = self.env['partner.name.used']
    #     if self.partner_name_used_ids:
    #         for one in self.partner_name_used_ids:
    #             if name_used == one.name_used and full_name_used == one.full_name_used:
    #                 break
    #             elif name_used == one.name_used and full_name_used != one.full_name_used:
    #                 one.full_name_used = full_name_used
    #             elif name_used != one.name_used and full_name_used == one.full_name_used:
    #                 one.name_used = name_used
    #             else:
    #                 name_used_line = name_used_obj.create({
    #                     'name_used': self.name,
    #                     'full_name_used': self.full_name,
    #                     'partner_id':self.id
    #                 })
    #         self.name_1 = self.name
    #         self.full_name_1 = self.full_name
    #     else:
    #         name_used_line = name_used_obj.create({
    #             'name_used': self.name,
    #             'full_name_used': self.full_name,
    #             'partner_id': self.id
    #         })
    #         self.name_1 = self.name
    #         self.full_name_1 = self.full_name
    #
    #     return res

    def _update_name_full_name(self):
        name_used = self.name_1
        full_name_used = self.full_name_1
        name_used_obj = self.env['partner.name.used']
        if self.partner_name_used_ids:
            for one in self.partner_name_used_ids:
                if name_used == one.name_used and full_name_used == one.full_name_used:
                    break
                elif name_used == one.name_used and full_name_used != one.full_name_used:
                    one.update({
                        'full_name_used': full_name_used,
                    })
                elif name_used != one.name_used and full_name_used == one.full_name_used:
                    one.update({
                        'name_used': name_used,
                    })
                else:
                    name_used_line = name_used_obj.create({
                        'name_used': self.name,
                        'full_name_used': self.full_name,
                        'partner_id': self.id
                    })
                    break
            self.name_1 = self.name
            self.full_name_1 = self.full_name
        else:
            name_used_line = name_used_obj.create({
                'name_used': self.name,
                'full_name_used': self.full_name,
                'partner_id': self.id
            })
            self.name_1 = self.name
            self.full_name_1 = self.full_name

    def update_name_full_name(self):
        name_used = self.name_1
        full_name_used = self.full_name_1
        name = self.name
        full_name = self.full_name
        name_used_obj = self.env['partner.name.used']
        if name_used != name or full_name_used != full_name:
            # if self.partner_name_used_ids:
            #     partner_name_used_ids = self.partner_name_used_ids.filtered(lambda x:x.name_used == name_used or x.full_name_used == full_name_used)
            #     print('partner_name_used_ids_akiny',partner_name_used_ids)
            #     if len(partner_name_used_ids) > 0:
            #         raise Warning('名称曾经用过')
            #     else:
            #         name_used_line = name_used_obj.create({
            #             'name_used': name_used,
            #             'full_name_used': full_name_used,
            #             'partner_id':self.id
            #         })
            #     self.name_1 = self.name
            #     self.full_name_1 = self.full_name
            # else:
            name_used_line = name_used_obj.create({
                'name_used': name_used,
                'full_name_used': full_name_used,
                'partner_id': self.id
            })
            self.name_1 = self.name
            self.full_name_1 = self.full_name
        else:
            self.name_1 = self.name
            self.full_name_1 = self.full_name

    # @api.one
    # def compute_child_delivery_ids(self):
    #     for one in self:
    #         child_delivery_ids = one.child_ids.filtered(
    #             lambda x: x.type == 'delivery')
    #         one.child_delivery_ids = child_delivery_ids
    #
    # def compute_child_contact_ids(self):
    #     for one in self:
    #         child_contact_ids = one.child_ids.filtered(
    #             lambda x: x.type == 'contact')
    #         one.child_contact_ids = child_contact_ids


# akiny 客户等级
class partner_level(models.Model):
    _name = 'partner.level'
    _description = '联系人等级'

    name = fields.Char(u'等级名称')
    type = fields.Selection([('customer', '客户'), ('supplier', '供应商')])
    description = fields.Text('描述')


# 来源
class partner_source(models.Model):
    _name = 'partner.source'
    _description = '客户供应商来源'

    name = fields.Char(u'名称')
    type = fields.Selection([('customer', '客户'), ('supplier', '供应商')])
    description = fields.Text('描述')


class PartnerNameUsed(models.Model):
    _name = 'partner.name.used'
    _description = '曾用名'

    partner_id = fields.Many2one('res.partner', 'partner')
    name_used = fields.Char(u'曾用简称')
    full_name_used = fields.Char(u'曾用全称')
