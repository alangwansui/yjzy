# -*- coding: utf-8 -*-
import math

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning
from odoo.osv import expression
from odoo.addons.purchase.models.purchase import PurchaseOrder

#13暂时不添加返点的计算
@api.onchange('partner_id', 'company_id')
def new_onchange_partner_id(self):
    if not self.partner_id:
        self.fiscal_position_id = False
        self.payment_term_id = False
        self.currency_id = False
        self.need_purchase_fandian = False
        self.purchase_fandian_ratio = 0
        self.purchase_fandian_partner_id = None
    else:
        self.fiscal_position_id = self.env['account.fiscal.position'].with_context(company_id=self.company_id.id).get_fiscal_position(
            self.partner_id.id)
        self.payment_term_id = self.partner_id.property_supplier_payment_term_id.id
        self.currency_id = self.partner_id.property_purchase_currency_id.id or self.env.user.company_id.currency_id.id
        partner = self.partner_id
        self.need_purchase_fandian = partner.need_purchase_fandian
        self.purchase_fandian_ratio = partner.purchase_fandian_ratio
        self.purchase_fandian_partner_id = partner.purchase_fandian_partner_id
    return {}

PurchaseOrder.onchange_partner_id = new_onchange_partner_id


Stage_Status_Default = 'draft'

Purchase_Selection = [('draft', '草稿'),
                  ('sent', 'RFQ Sent'),
                  ('submit', u'带责任人审批'),
                  ('sales_approve', u'待产品经理审批'),
                  ('approve', '待出运'),  # akiny 翻译成等待出运
                  ('purchase', '开始出运'),
                  ('done', '锁定'),
                  ('cancel', '取消'),
                  ('refused', u'已拒绝')]

class PurchaseOrderStage(models.Model):
    _name = "purchase.order.stage"
    _description = "Purchase Order Stage"
    _order = 'sequence'

    name = fields.Char('Stage Name', translate=True, required=True)
    code = fields.Char('code')
    sequence = fields.Integer(help="Used to order the note stages", default=1)
    state = fields.Selection(Purchase_Selection, 'State', default=Stage_Status_Default) #track_visibility='onchange',
    fold = fields.Boolean('Folded by Default')
    # _sql_constraints = [
    #     ('name_code', 'unique(code)', u"编码不能重复"),
    # ]
    user_ids = fields.Many2many('res.users', 'ref_po_users', 'fid', 'tid', 'Users') #可以进行判断也可以结合自定义视图模块使用
    group_ids = fields.Many2many('res.groups', 'ref_po_group', 'gid', 'bid', 'Groups')
    main_sign_uid = fields.Many2one('res.users', u'主签字人')


class purchase_order(models.Model):
    _inherit = 'purchase.order'
    #13已经添加
    @api.depends('order_line')
    def compute_so(self):
        for o in self:
            o.so_ids = o.order_line.mapped('sol_id').mapped('order_id')
            o.supplierinfo_ids = o.order_line.mapped('supplierinfo_id') #在采购合同通过供应商信息来查找采购合同

#----
    def compute_info(self):
        aml_obj = self.env['account.move.line']
        for one in self:
            polines = one.order_line
            sml_lines = aml_obj.search([('po_id', '=', one.id)]).filtered(lambda x: x.account_id.code == '1123')
            print('sml_lines__11717171',sml_lines)
            if one.yjzy_payment_ids and one.yjzy_payment_ids[0].currency_id.name == 'CNY':
                balance = sum([x.debit - x.credit for x in sml_lines])
            else:
                balance = sum([1 * x.amount_currency for x in sml_lines])
            no_deliver_amount = sum([x.price_unit * (x.product_qty - x.qty_received) for x in polines])

            one.balance = balance
            one.no_deliver_amount = no_deliver_amount
  #13ok
    @api.depends('aml_ids','aml_ids.credit','aml_ids.debit','aml_ids.amount_currency')
    def compute_balance(self):
        for one in self:
            sml_lines = one.aml_ids.filtered(lambda x: x.account_id.code == '1123')
            if one.yjzy_payment_ids and one.yjzy_payment_ids[0].currency_id.name == 'CNY':
                balance = sum([x.debit - x.credit for x in sml_lines])
                real_advance = sum([x.debit for x in sml_lines])
            else:
                balance = sum([1 * x.amount_currency for x in sml_lines])
                real_advance = sum([1 * i.amount_currency for i in sml_lines.filtered(lambda x: x.amount_currency >0)])
            one.balance_new = balance
            one.real_advance = real_advance



    @api.depends('order_line.qty_received','source_so_id','order_line.product_qty','order_line')
    def compute_no_deliver_amount(self):
        for one in self:
            one.no_deliver_amount_new = sum([x.price_unit * (x.product_qty - x.qty_received) for x in one.order_line])
    #13ok
    @api.depends('payment_term_id', 'amount_total')
    def compute_pre_advance(self):
        for one in self:
            if one.payment_term_id:
                one.pre_advance = one.payment_term_id.get_advance(one.amount_total)
            else:
                one.pre_advance = 0


    # is_cip = fields.Boolean(u'报关', default=False)
    # is_fapiao = fields.Boolean(u'含税')
    #akiny 修改state
    #state = fields.Selection(selection_add=[('edit', u'可修改'),('approve_sales',u'责任人审批完成'),('submit',u'已提交'),('refused',u'已拒绝')])

    #
    # invoice_line_ids = fields.One2many('account.invoice.line','purchase_id',u'账单明细行')
    @api.model
    def _default_purchase_order_stage(self):
        stage = self.env['purchase.order.stage']
        return stage.search([], limit=1)

    @api.depends('source_so_id','source_so_id.amount_total')
    def compute_so_id_amount_total(self):
        for one in self:
            one.so_id_amount_total = one.source_so_id.amount_total

    @api.depends('order_line','order_line.sol_id_price_total')
    def compute_sol_ids_amount_total(self):
        for one in self:
            sol_ids_amount_total = sum(x.sol_id_price_total for x in one.order_line)
            one.sol_ids_amount_total = sol_ids_amount_total


    @api.depends('hxd_ids','hxd_ids.amount_total_org_new')
    def compute_amount_org_hxd(self):
        for one in self:
            amount_total_org_new = sum(x.amount_total_org_new for x in one.hxd_ids)
            one.amount_org_hxd = amount_total_org_new

    @api.depends('partner_id')
    def compute_need_change_partner(self):
        for one in self:
            for x in one.order_line:
                if x.sol_id.supplier_id != one.partner_id:
                    one.need_change_partner = True
                    continue




    stage_id = fields.Many2one(
        'purchase.order.stage',
        default=_default_purchase_order_stage, copy=False)

    state_1 = fields.Selection(Purchase_Selection, u'审批流程', default='draft', index=True, related='stage_id.state',
                               track_visibility='onchange')  # 费用审批流程

    balance = fields.Monetary(u'预付余额', compute=compute_info, currency_field='yjzy_currency_id')

    need_change_partner = fields.Boolean('需要同步供应商',compute=compute_need_change_partner)
    #akiny_new

    hxd_ids = fields.One2many('account.reconcile.order.line','po_id','所有已经批准的核销单',domain=[('order_id.state_1','in',['done','post'])])
    amount_org_hxd = fields.Float('核销单的付款金额总和',compute=compute_amount_org_hxd,store=True)
    need_purchase_fandian = fields.Boolean(u'采购返点')
    purchase_fandian_ratio = fields.Float(u'返点比例：%')
    purchase_fandian_partner_id = fields.Many2one('res.partner', u'返点对象')



    revise_content = fields.Text(u'合同变更')
    revise_count = fields.Integer(u'变更次数')
    revise_date = fields.Date(u'变更日期')
    revise_reason = fields.Html(u'变更原因')

    main_sign_uid = fields.Many2one('res.users', u'主签字人')
    user_ids = fields.Many2many('res.users', 'ref_user_po', 'pid', 'uid', u'用户')

    is_editable = fields.Boolean(u'可编辑',related='source_so_id.is_editable')


    #已经添加13
    gongsi_id = fields.Many2one('gongsi', '内部公司')
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('check', '检查'),
        ('sent', 'RFQ Sent'),
        ('submit', u'带责任人审批'),
        ('approve_sales', u'待产品经理审批'),
        ('to approve', 'To Approve'),  # akiny 翻译成等待出运
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'), ('refused', u'已拒绝')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')
    contract_code = fields.Char(u'合同编码')
    term_purchase = fields.Html(u'采购条款')
    so_ids = fields.Many2many('sale.order', compute=compute_so, stirng=u'销售订单', copy=False)
    supplierinfo_ids = fields.Many2many('product.supplierinfo', 'rel_info_po', 'po_id', 'info_id', u'供应商产品编码',
                                        compute=compute_so, store=True)
    can_confirm_by_so = fields.Boolean(u'已可以自动随SO审批')
    box_type = fields.Selection([('b', 'B'), ('a', 'A')], string=u'编号方式', default='b')
    contact_id = fields.Many2one(u'res.partner', '联系人')
    include_tax = fields.Boolean(u'含税')
    sale_uid = fields.Many2one('res.users', u'业务员',default=lambda self: self.env.user.assistant_id.id)
    sale_assistant_id = fields.Many2one('res.users', u'业务助理',default=lambda self: self.env.user.id)
    yjzy_payment_ids = fields.One2many('account.payment', 'po_id', u'预付款单')
    yjzy_currency_id = fields.Many2one('res.currency', u'预收币种', related='yjzy_payment_ids.currency_id')
    balance_new = fields.Monetary(u'预付余额_新', compute='compute_balance', currency_field='yjzy_currency_id',store=True)
    real_advance = fields.Monetary(u'预付金额', compute='compute_balance', currency_field='yjzy_currency_id',store=True)
    pre_advance = fields.Monetary(u'预付金额', currency_field='currency_id', compute=compute_pre_advance, store=True, help=u"根据付款条款计算的可预付金额\n")#计划预付金额，根据付款条款计算

    #以下还没有进入文档
    submit_date = fields.Date('提交审批时间')
    submit_uid = fields.Many2one('res.users', u'提交审批')

    purchaser_date = fields.Date('采购审批时间')
    purchaser_uid = fields.Many2one('res.users', u'采购审批')

    second_sign_uid = fields.Many2one('res.users', u'次签字人')

    no_deliver_amount = fields.Float('未发货金额', compute=compute_info)
    no_deliver_amount_new = fields.Float('未发货金额', compute=compute_no_deliver_amount, store=True)

    partner_payment_term_id = fields.Many2one('account.payment.term', u'客户付款条款',
                                              related='partner_id.property_supplier_payment_term_id')
    is_different_payment_term = fields.Boolean('付款条款是否不同')

    #akiny
    so_id_state = fields.Selection('源销售合同状态',related='source_so_id.state')
    aml_ids = fields.One2many('account.move.line', 'po_id', u'分录明细', readonly=True)
    so_currentcy_id = fields.Many2one('res.currency','销售合同币种',related='source_so_id.currency_id')
    so_id_amount_total = fields.Monetary('对应销售金额',currency_field='so_currentcy_id', compute=compute_so_id_amount_total,store=True)
    sol_ids_amount_total = fields.Monetary('对应销售金额', currency_field='so_currentcy_id', compute=compute_sol_ids_amount_total,
                                         store=True)
    date_factory_return = fields.Date('工厂回传时间', index=True,)

    #采购单更换了供应商，需要更新对应的销售明细上的供应商
    def change_supplier(self):
        if self.need_change_partner:
            for one in self.order_line:
                one.sol_id.supplier_id = self.partner_id
        self.need_change_partner = False

    def _stage_find(self, domain=None, order='sequence'):
        search_domain = list(domain)
        return self.env['purchase.order.stage'].search(search_domain, order=order, limit=1)

        # 新的审批流程

    def action_submit_stage(self):
        if not self.contract_code:
            raise Warning('合同号不为空！')
        if not self.payment_term_id:
            raise Warning('付款条款不为空！')
        for line in self.order_line:
            if line.dlr_str == '':
                raise Warning('采购和销售没有完全对应！')
        stage_id = self._stage_find(domain=[('code', '=', '020')])
        return self.write({'stage_id': stage_id.id,
                           'state': 'submit',
                           'submit_uid': self.env.user.id,
                           'submit_date': fields.datetime.now()})

    def action_sales_approve_stage(self):
        stage_id = self._stage_find(domain=[('code', '=', '040')])
        if not stage_id.user_ids:
            raise Warning('请先设置采购签字人员！')
        print('stage_id.user_ids', stage_id.user_ids)
        main_sign_uid = stage_id.main_sign_uid
        return self.write({'stage_id': stage_id.id,
                           'can_confirm_by_so': True,
                           'purchaser_uid': self.env.user.id,
                           'purchaser_date': fields.datetime.now(),
                           'state': 'to approve',
                           'main_sign_uid': main_sign_uid.id
                           })

    def action_sales_approve_stage_old(self):
        stage_id = self._stage_find(domain=[('code', '=', '030')])
        return self.write({'stage_id': stage_id.id,
                           'state': 'approve_sales',
                           })


    def action_approve_stage(self):
        stage_id = self._stage_find(domain=[('code', '=', '040')])
        if not stage_id.user_ids:
            raise Warning('请先设置采购签字人员！')
        print('stage_id.user_ids',stage_id.user_ids)
        main_sign_uid = stage_id.main_sign_uid
        return self.write({'stage_id': stage_id.id,
                           'can_confirm_by_so': True,
                           'purchaser_uid': self.env.user.id,
                           'purchaser_date': fields.datetime.now(),
                           'state': 'to approve',
                           'main_sign_uid':main_sign_uid.id
                           })

    def action_confirm_stage(self):
        if self.state == 'to approve':
            self.button_approve()
        stage_id = self._stage_find(domain=[('code', '=', '050')])
        return self.write({'stage_id': stage_id.id,
                           })


    def action_refuse_stage(self, reason):
        stage_id = self._stage_find(domain=[('code', '=', '090')])
        stage_preview = self.stage_id
        user = self.env.user
        group = self.env.user.groups_id
        if user not in stage_preview.user_ids:
            raise Warning('您没有权限拒绝')
        else:
            self.write({'state': 'refused',
                        'submit_date': False,
                        'submit_uid': False,
                        'purchaser_uid': False,
                        'purchaser_date': False,
                        'main_sign_uid':False,
                        'stage_id': stage_id.id})
        for so in self:
            so.message_post_with_view('yjzy_extend.po_template_refuse_reason',
                                      values={'reason': reason, 'name': self.contract_code},
                                      subtype_id=self.env.ref(
                                          'mail.mt_note').id)  # 定义了留言消息的模板，其他都可以参考，还可以继续参考费用发送计划以及邮件方式

    def action_to_draft_stage(self):
        stage_id = self._stage_find(domain=[('code', '=', '010')])
        self.write({ 'state': 'draft',
                     'stage_id': stage_id.id})


    def action_to_cancel_stage(self):
        if self.create_uid.id != self.env.user.id:
            raise Warning('只有创建者才允许取消！')
        if self.state not in ['draft','refused']:
            raise Warning('只有草稿或者拒绝状态的才能取消')
        self.button_cancel()
        stage_id = self._stage_find(domain=[('code', '=', '100')])
        self.write({
            'submit_date': False,
            'submit_uid': False,
            'purchaser_uid': False,
            'purchaser_date': False,
            'main_sign_uid':False,
            'stage_id': stage_id.id})



    def update_back_tax(self):
        self.ensure_one()
        for line in self.order_line:
            line.back_tax = self.source_so_id.cip_type != 'none' and line.product_id.back_tax or 0

        self.compute_info()


  #  partner_payment_term_id_value = fields.Many2one('account.payment.term', u'客户付款条款值')

    #13已经添加
    @api.constrains('contract_code')
    def check_contract_code(self):
        for one in self:
            if self.search_count([('contract_code', '=', one.contract_code)]) > 1:
                raise Warning('合同编码重复')
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if operator in ('ilike', 'like', '=', '=like', '=ilike'):
            domain = expression.AND([
                args or [],
                ['|', ('name', operator, name), ('contract_code', operator, name)]
            ])
            return self.search(domain, limit=limit).name_get()
        return super(purchase_order, self).name_search(name, args, operator, limit)
    @api.multi
    def name_get(self):
        ctx = self.env.context
        res = []
        for order in self:
            if ctx.get('only_code'):
                name = order.contract_code
            elif ctx.get('purchase_code_balance'):
                name = '%s[%s]' % (order.contract_code, order.balance)
            else:
                # name = '%s[%s]' % (order.name, order.contract_code)
                if order.contract_code:
                    name = '%s' % (order.contract_code)
                else:
                    name = '%s' % ('无合同号')
            res.append((order.id, name))
        return res

    def clear_po_box(self):
        for line in self.order_line:
            line.box_start = 0
            line.box_end = 0

    def open_wizard_po_box(self):
        self.ensure_one()
        return {
            'name': _(u'生成箱号'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.po.box',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }



    @api.onchange('payment_term_id')
    def onchange_payment_term_id(self):
        #self.partner_payment_term_id_value = self.payment_term_id
        if self.payment_term_id != self.partner_payment_term_id:
            self.is_different_payment_term = True
        else:
            self.is_different_payment_term = False




#以下暂时不要
    @api.onchange('partner_id', 'company_id')
    def onchange_partner_id(self):
        res = super(purchase_order, self).onchange_partner_id()
        self.contact_id = self.partner_id.child_ids and self.partner_id.child_ids[0]
        self.need_purchase_fandian = self.partner_id.need_purchase_fandian
        self.purchase_fandian_ratio = self.partner_id.purchase_fandian_ratio
        self.purchase_fandian_partner_id = self.partner_id.purchase_fandian_partner_id

        return res

    def make_box_number_b(self):
        self.ensure_one()
        ICQ = self.env['ir.config_parameter'].sudo()
        start = end = int(float(ICQ.get_param('po.box')))
        # print('>>>>>>>>', start, end)
        for line in self.order_line:
            if line.product_id.type != 'product':
                continue

            if line.box_start:
                raise Warning(u'已经存在箱号,请勿重复编号')
            box_qty = line.product_id.get_package_info(line.product_qty)['max_qty']

            end += box_qty - 1
            line.box_start = start
            line.box_end = end
            start += box_qty - 1
            start += 1
            end += 1

        ICQ.set_param('po.box', end + 1)


    def make_yfsqd(self):
        yfsqd_ids = []
        for one in self:
            #不重复生成
            if one.yjzy_payment_ids:
                continue

            if one.partner_id.auto_yfsqd:

                journal = self.env['account.journal'].search([('code', '=', 'yfdrl'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
                if not journal:
                    raise Warning('没有找到对应的日记账 编码:%s  公司:%s' % ('yfdrl', self.env.user.company_id.name))

                advance_account = self.env['account.account'].search([('code','=', '1123'),('company_id', '=', self.env.user.company_id.id)], limit=1)
                if not advance_account:
                    raise Warning('没有找到对应的科目 编码:%s  公司:%s' % ('1123', self.env.user.company_id.name))


                yfsqd = self.env['account.payment'].with_context(default_sfk_type='yfsqd').create({
                    'payment_type': 'outbound',
                    'partner_type':  'supplier',
                    'partner_id': one.partner_id.id,
                    'payment_method_id': 2,
                    'include_tax':  one.include_tax,
                    'amount': one.pre_advance,
                    'po_id': one.id,
                    'sale_uid': one.sale_uid.id,
                    'sale_assistant_uid':  one.sale_assistant_id.id,
                    'currency_id': one.currency_id.id,
                    'journal_id': journal.id,
                    'sale_assistant_id': one.sale_assistant_id,
                    'advance_ok': True,
                    'advance_account_id': advance_account.id,
                    'company_id': self.env.user.company_id.id,
                })
                yfsqd_ids.append(yfsqd.id)

        return {
            'name': u'预付申请',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'domain': [('id','in', yfsqd_ids)],
        }
#------------------
    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        if 'contract_code' not in default:
            default['contract_code'] = "%s(copy)" % self.contract_code
        return super(purchase_order, self).copy(default)


    def unlink(self):
        for one in self:
            if one.state != 'cancel':
                raise Warning(u'只有取消状态允许删除')
        return super(purchase_order, self).unlink()


    @api.model
    def create(self, valus):
        po = super(purchase_order, self).create(valus)
        partner = po.partner_id
        po.need_purchase_fandian = partner.need_purchase_fandian
        po.purchase_fandian_ratio = partner.purchase_fandian_ratio
        po.purchase_fandian_partner_id = partner.purchase_fandian_partner_id
        return po
    #13ok
    @api.model
    def cron_compute_pre_advance(self):
        self.search([]).compute_pre_advance()
        return True


    def test_pre_advance(self):
        self.ensure_one()
        self.compute_info()
        return True


    def is_from_so(self):
        return self.source_so_id and True or False

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        res = super(purchase_order, self).search(args, offset=offset, limit=limit, order=order, count=count)
        # print('===args', args)
        # arg_dic = args and dict([(x[0], x[2]) for x in args if isinstance(x, list)]) or {}
        # pdt_value = arg_dic.get('product_info_id')
        # if pdt_value:
        #     sol_records = self.env['sale.order.line'].search([('product_id.attribute_value_ids', 'like', pdt_value)])
        #     res |= sol_records.mapped('order_id')
        return res


    def set_tax_zero(self):
        zero_tax = self.env['account.tax'].search([('code', '=', 'purchase_zero')])
        if not zero_tax:
            raise Warning(u'没找到0税编码，请检查税率设置')
            raise Warning(u'没找到0税编码，请检查税率设置')
        for line in self.order_line:
            line.taxes_id = zero_tax

    def compute_package_info(self):
        self.order_line.compute_package_info()
#这个是特殊审批 直接创建预付申请单。暂时取消
    @api.multi
    def button_confirm(self):
        res = super(purchase_order, self).button_confirm()
        self.make_yfsqd()
        return res

    def clear_yfsqd(self):
        for one in self.yjzy_payment_ids:
            if one.state != 'draft':
                raise Warning(u'不能删除非草稿的预付申请单')

        self.yjzy_payment_ids.unlink()
        return True



    @api.model
    def cron_update_purchase_gongsi_id(self):
        for one in self:
            print('===', one)
            one.gongsi_id = one.source_so_id.purchase_gongsi_id






class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('product_id', )
    def compute_supplierinfo(self):
        product_info_obj = self.env['product.supplierinfo']
        for one in self:
            info = product_info_obj.search([('product_id', '=', one.product_id.id), ('name', '=', one.partner_id.id)], limit=1)
            # print ('===>', info)
            one.supplierinfo_id = info

    @api.depends('sol_id','sol_id.price_total')
    def compute_sol_id_price_total(self):
        for one in self:
            one.sol_id_price_total = one.sol_id.price_total

    s_uom_id = fields.Many2one('product.uom', u'销售打印单位', related='product_id.s_uom_id')
    p_uom_id = fields.Many2one('product.uom', u'采购打印单位', related='product_id.p_uom_id')

    sol_id = fields.Many2one('sale.order.line', u'销售明细', copy=False)
    sol_currency_id = fields.Many2one('res.currency',related='sol_id.currency_id')
    sol_id_price_total = fields.Monetary(u'对应销售金额',currency_field='sol_currency_id',compute=compute_sol_id_price_total, store=True)


    so_id = fields.Many2one('sale.order', related='sol_id.order_id', string=u'销售订单', readonly=True)
    back_tax = fields.Float(u'退税率', digits=dp.get_precision('Back Tax'))

    last_purchase_price = fields.Float('最后采购价', related='product_id.last_purchase_price')
    qty_available = fields.Float('在手数', related='product_id.qty_available')
    virtual_available = fields.Float('预测数', related='product_id.virtual_available')

    supplierinfo_id = fields.Many2one('product.supplierinfo', '供应商产品信息', compute=compute_supplierinfo, )
    price_section_base = fields.Float('基价区间')

    box_start = fields.Integer('开始箱号')
    box_end = fields.Integer(u'结束箱号')

    min_package_name = fields.Char(u'小包装名称')
    max_package_qty = fields.Float(u'大包装名称')
    qty_max_package = fields.Float(u'箱数')
    max_package_volume = fields.Float(u'大包装体积')#902akiny  算大包装的体积

    max_qty = fields.Float(u'大包数')
    max_qty2 = fields.Float(u'大包数参考')
    max_qty_ng = fields.Boolean(u'非整包')

    need_print = fields.Boolean('是否打印', default=True)



    def compute_package_info(self):
        for one in self:
            if one.product_id.type != 'product':
                continue
            res = one.product_id.get_package_info(one.product_qty)
            one.min_package_name = res['min_record'] and res['min_record'].name or '-'
            one.max_package_qty = res['max_package']
            one.qty_max_package = math.ceil(res['max_qty'])
            one.max_qty_ng = res['max_qty_ng']
            one.max_qty = res['max_qty']
            one.max_qty2 = res['max_qty2']
            one.max_package_volume = res['volume']

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super(purchase_order_line, self).onchange_product_id()
        if self.product_id:
            self.back_tax = self.product_id.back_tax

        self.need_split_bom = self.product_id.need_split_bom
        self.need_print = self.product_id.need_print
        return res
   #以上已经添加
    @api.onchange('price_section_base')
    def onchange_price_section_base(self):
        if self.product_id and self.price_section_base:
            sections = self.product_id.price_section_ids.filtered(lambda x: x.start <= self.price_section_base < x.end)
            if sections:
                self.price_unit = sections[0].price

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




###############################
