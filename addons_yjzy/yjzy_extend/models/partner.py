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
         ('delivery', u'收货地址'),
         ], string='Address Type',
        default='contact',
        help="Used to select automatically the right address according to the context in sales and purchases documents.")

    jituan_id = fields.Many2one('ji.tuan', '集团')
    comment_contract = fields.Text(u'对接内容描述')
    devloper_id = fields.Many2one('res.users', u'开发人员')
    full_name = fields.Char('公司全称')
    invoice_title = fields.Char(u'发票抬头')
    mark_ids = fields.Many2many('transport.mark', 'ref_mark_patner', 'pid', 'mid', u'唛头')
    mark_comb_ids = fields.Many2many('mark.comb', 'ref_comb_partner', 'pid', 'cid', u'唛头组')
    exchange_type_ids = fields.Many2many('exchange.type', 'ref_exchange_partner', 'pid', 'eid', u'交货方式')
    exchange_demand_ids = fields.One2many('exchange.demand', 'partner_id', u'交单要求')

    demand_info = fields.Text(u'交单要求')
    notice_man = fields.Char(u'通知人')
    delivery_man = fields.Char(u'发货人')

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
    state = fields.Selection([('draft', u'草稿'), ('done', u'完成')], u'状态', default='draft')
    auto_yfsqd = fields.Boolean(u'自动生成预付')
    is_inter_partner = fields.Boolean(u'是否内部')
    jituan_name = fields.Char(u'集团名称')

    contract_type = fields.Selection([('a', '模式1'), ('b', '模式2'), ('c', '模式3')], '合同类型', default='c')
    gongsi_id = fields.Many2one('gongsi', '销售主体')
    purchase_gongsi_id = fields.Many2one('gongsi', '采购主体')

    sale_currency_id = fields.Many2one('res.currency','销售币种',related='property_product_pricelist.currency_id')
    customer_product_ids = fields.One2many('product.product','customer_id','客户采购产品')

    customer_info_from = fields.Char(u'客户来源')
    customer_info_from_uid = fields.Many2one('res.users',u'客户获取人')


    customer_purchase_in_china = fields.Float(u'客户在中国采购规模',currency_field='customer_purchase_in_china_currency_id')
    customer_purchase_in_china_currency_id = fields.Many2one('res.currency', '客户在中国采购规模')

    customer_sale_total = fields.Float(u'客户销售额',currency_field='customer_sale_total_currency_id')
    customer_sale_total_currency_id = fields.Many2one('res.currency', '客户销售额')

    child_delivery_ids = fields.One2many('res.partner', 'parent_id', domain=[('type', '=', 'delivery')], string='收货地址')
    child_contact_ids = fields.One2many('res.partner', 'parent_id', domain=[('type', '=', 'contact')], string='联系人')

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
            pricelist = p_obj.create({
                'name': one.name,
                'customer_id': one.id,
                'currency_id':  self.sale_currency_id.id or self.env.user.company_id.currency_id.id,
                'type': 'special',
            })
            one.property_product_pricelist = pricelist


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












