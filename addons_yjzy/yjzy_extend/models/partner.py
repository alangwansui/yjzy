# -*- coding: utf-8 -*-

from odoo import models, fields, api


class res_partner(models.Model):
    _inherit = 'res.partner'
    _order = "sequence, display_name"

    def compute_amount_purchase_advance(self):
        aml_obj = self.env['account.move.line']
        for one in self:
            lines = aml_obj.search([('partner_id', '=', one.id), ('account_id.code', '=', '1123')])
            one.advance_currency_id = one.property_purchase_currency_id or one.currency_id
            one.amount_purchase_advance_org = sum(
                [line.get_amount_to_currency(one.advance_currency_id) for line in lines])
            one.amount_purchase_advance = sum([line.get_amount_to_currency(one.currency_id) for line in lines])

    #增加地址翻译

    code = fields.Char('编码')
    street = fields.Char(translate=True)
    street2 = fields.Char(translate=True)
    city = fields.Char(translate=True)


    assistant_id = fields.Many2one('res.users', store=True)
    product_manager_id = fields.Many2one('res.users', related='user_id.product_manager_id', store=True)

    type = fields.Selection(selection_add=[('notice', u'发货代理')])
    type1 = fields.Selection(
         [('contact', u'联系人'),
         ('invoice', u'发票主体'),
         ('delivery', u'收货地址'),
         ], string='Address Type',
        default='contact',
        help="Used to select automatically the right address according to the context in sales and purchases documents.")

    jituan_id = fields.Many2one('ji.tuan', '集团')
    comment_contact = fields.Text(u'对接内容描述')
    devloper_id = fields.Many2one('res.users', u'开发人员')
    full_name = fields.Char('公司全称')
    invoice_title = fields.Char(u'发票抬头')
    mark_ids = fields.Many2many('transport.mark', 'ref_mark_patner', 'pid', 'mid', u'唛头')
    mark_comb_ids = fields.Many2many('mark.comb', 'ref_comb_partner', 'pid', 'cid', u'唛头组')

    #mark_comb_id = fields.Many2one('mark.comb',u'唛头')

    exchange_type_ids = fields.Many2many('exchange.type', 'ref_exchange_partner', 'pid', 'eid', u'交单方式')
    exchange_demand_ids = fields.One2many('exchange.demand', 'partner_id', u'交单要求')

    demand_info = fields.Text(u'交单要求')
    notice_man = fields.Text(u'通知人')
    delivery_man = fields.Text(u'收货人')

    wharf_src_id = fields.Many2one('stock.wharf', u'装船港')
    wharf_dest_id = fields.Many2one('stock.wharf', u'目的港')

    advance_currency_id = fields.Many2one('res.currency', compute=compute_amount_purchase_advance, string=u'外币')
    amount_purchase_advance_org = fields.Monetary('预付金额:外币', currency_field='advance_currency_id',
                                                  compute=compute_amount_purchase_advance)
    amount_purchase_advance = fields.Monetary('预付金额:本币', currency_field='currency_id',
                                              compute=compute_amount_purchase_advance)

    term_description = fields.Html(u'销售条款')
    term_purchase = fields.Html(u'采购条款')

    fax = fields.Char(u'传真')
    wechat = fields.Char(u'微信')
    qq = fields.Char(u'QQ')
    skype = fields.Char('Skype')
    level = fields.Selection([(x, x.upper()) for x in 'abcde'], u'客户等级')

    sequence = fields.Integer(u'排序', default=10, index=True)


    need_purchase_fandian = fields.Boolean(u'采购返点')
    purchase_fandian_ratio = fields.Float(u'返点比例：%')
    purchase_fandian_partner_id = fields.Many2one('res.partner', u'返点对象')
    state = fields.Selection([('draft', u'草稿'),
                              ('check',u'提交前必填项检查'),
                              ('submit',u'已提交'),
                              ('to approve',u'责任人已审批'),
                              ('approve',u'合规审批完成'),('done', u'完成'),('refuse', u'拒绝'),('cancel', u'取消')], string=u'状态', track_visibility='onchange', default='draft')
    auto_yfsqd = fields.Boolean(u'自动生成预付')
    is_inter_partner = fields.Boolean(u'是否内部')
    jituan_name = fields.Char(u'集团名称')

    contract_type = fields.Selection([('a', '模式1'), ('b', '模式2'), ('c', '模式3')], '合同类型', default='c')
    gongsi_id = fields.Many2one('gongsi', '销售主体')
    purchase_gongsi_id = fields.Many2one('gongsi', '采购主体')

    sale_currency_id = fields.Many2one('res.currency','销售币种')
    customer_product_ids = fields.One2many('product.product','customer_id','客户采购产品')

    campaign_id = fields.Many2one('utm.campaign',u'客户来源')
    customer_info_from_uid = fields.Many2one('res.users',u'客户获取人')


    customer_purchase_in_china = fields.Char(u'客户在中国采购规模(CNY)')
    customer_purchase_in_china_currency_id = fields.Many2one('res.currency', '客户在中国采购规模币种',default=lambda self: self.env.user.company_id.currency_id.id)
    customer_purchase_in_china_note = fields.Text(u'备注')

    customer_sale_total = fields.Char(u'客户销售额(CNY)')
    customer_sale_total_currency_id = fields.Many2one('res.currency', '客户销售额币种',
                                                      default=lambda self: self.env.user.company_id.currency_id.id)
    customer_sale_total_note = fields.Text(u'备注')


    supplier_sale_total = fields.Char(u'供应商销售额(CNY)',
                                                 currency_field='supplier_sale_total_currency_id')
    supplier_sale_total_currency_id = fields.Many2one('res.currency', '供应商销售额币种', default=lambda
        self: self.env.user.company_id.currency_id.id)
    supplier_sale_total_note = fields.Text(u'备注')

    supplier_export_total = fields.Char(u'供应商出口额(CNY)',
                                           currency_field='supplier_export_total_currency_id')
    supplier_export_total_currency_id = fields.Many2one('res.currency', '供应商出口额币种', default=lambda
        self: self.env.user.company_id.currency_id.id)
    supplier_export_total_note = fields.Text(u'备注')



    child_delivery_ids = fields.One2many('res.partner', 'parent_id', domain=[('type', '=', 'delivery')], string='收货地址')
    child_contact_ids = fields.One2many('res.partner', 'parent_id', domain=[('type', '=', 'contact')], string='联系人')
    child_invoice_ids = fields.One2many('res.partner', 'parent_id', domain=[('type', '=', 'invoice')], string='发票主体')
    #akiny
    customer_product_origin_ids = fields.One2many('partner.product.origin','partner_id', u'客户产品')
    address_text = fields.Text(u'地址')
    mark_html = fields.Html('唛头')
    mark_text = fields.Text(u'唛头')
    city_product_origin = fields.Char('产地')

    payee1 = fields.Char('收款人')
    payee1_address = fields.Text('收款人地址')
    account1 = fields.Char('账户')
    swift1 = fields.Char('SWIFT(非中国大陆供应商)')
    bank1 = fields.Char('银行')
    bank1_address = fields.Char('银行地址')
    supplier_info_from_uid = fields.Many2one('res.users',u'客户获取人')
    attachment_business_license = fields.Many2many('ir.attachment',string='营业执照以及其他资料附件')
    actual_controlling_person = fields.Char(u'实际控股人')

    other_attachment = fields.Many2many('ir.attachment',string='其他补充资料附件')
    partner_hs = fields.Many2many('hs.hs',string='产品品名')
    other_social_accounts = fields.Char(u'社交帐号')
    partner_level = fields.Many2one('partner.level','等级')
    is_editable = fields.Boolean(u'是否允许编辑')

    @api.onchange('invoice_title')
    def onchange_invoice_title(self):
        if self.type == 'delivery':
            self.name = self.invoice_title

    @api.onchange('sale_currency_id')
    def onchange_sale_currency(self):
        if self.sale_currency_id:
            pricelist = self.env['product.pricelist'].search([('customer_id', '=', self._origin.id), ('currency_id', '=', self.sale_currency_id.id)], limit=1)


            print('====', pricelist, [('customer_id', '=', self.id), ('currency_id', '=', self.sale_currency_id.id)])

            if pricelist:
                self.property_product_pricelist = pricelist


    @api.model
    def create(self, vals):
        one = super(res_partner, self).create(vals)
        if one.customer and one.company_type == 'company':
            one.create_my_pricelist()
            one.generate_code()
        return one


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
                'currency_id':  currency_cny.id,
                'type': 'special',
            })
            pricelist_usd = p_obj.create({
                'name': one.name,
                'customer_id': one.id,
                'currency_id':  currency_usd.id,
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


    @api.multi


    def action_check(self):
        if self.create_uid == self.env.user:
           self.state = 'check'
        else:
           raise Warning('必须是创建人才能提交')
    def action_submit(self):
        if self.create_uid == self.env.user:
           self.state = 'submit'
        else:
           raise Warning('必须是创建人才能提交')

    def action_to_approve(self):
        if self.user_id == self.env.user:
           return self.write({'state': 'to_approve'})
        else:
           raise Warning('必须是责任人才能审批')
    def action_approve(self):
        return self.write({'state': 'approve'})
    def action_done(self):
        return self.write({'state': 'done'})
    def action_refuse(self):
        return self.write({'state': 'refuse'})

    def action_cancel(self):
        if self.create_uid == self.env.user:
           return self.write({'state': 'cancel'})
        else:
           raise Warning('必须是创建人才能取消')
    def action_draft(self):
        partner = self.filtered(lambda s: s.state in ['cancel'])
        if self.create_uid == self.env.user:
           return partner.write({
            'state': 'draft',})
        else:
           raise Warning('必须是创建人才能提交')
    #def unlink(self):
    #    for one in self:
    #        if one.state != 'cancel':
     #           raise Warning('不能删除非取消状态发运单')
    #    return super(res_partner, self).unlink()




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

    @api.onchange('type1')
    def _onchange_type1(self):
        self.type = self.type1


    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id.code == 'CN':
           self.lang = 'zh_CN'
        else:
           self.lang = 'en_US'

    @api.one
    def compute_child_delivery_ids(self):
        for one in self:
            child_delivery_ids = one.child_ids.filtered(
                lambda x: x.type == 'delivery')
            one.child_delivery_ids =  child_delivery_ids

    def compute_child_contact_ids(self):
        for one in self:
            child_contact_ids = one.child_ids.filtered(
                lambda x: x.type == 'contact')
            one.child_contact_ids =  child_contact_ids





#akiny 客户等级
class partner_product_origin(models.Model):
    _name = 'partner.level'
    _description = '联系人等级'



    name = fields.Char(u'等级名称')
    type = fields.Selection([('customer','客户'),('supplier','供应商')])
    description = fields.Text('描述')













