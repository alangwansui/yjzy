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
    gongsi_id = fields.Many2one('gongsi', '内部公司')
    purchase_gongsi_id = fields.Many2one('gongsi', '内部采购公司')


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












