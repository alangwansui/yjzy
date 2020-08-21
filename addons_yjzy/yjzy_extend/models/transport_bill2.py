# -*- coding: utf-8 -*-
from num2words import num2words
from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning


class transport_bill(models.Model):
    _inherit = 'transport.bill'

    def _compute_overall_profit(self):
        for one in self:
            hsname_all_ids = one.hsname_all_ids
            all_back_tax_invoice_ids = one.all_back_tax_invoice_ids.filtered(lambda x: x.yjzy_type =='back_tax' and x.invoice_attribute == 'other_po')
            purchase_amount_max_forecast_total = sum(x.purchase_amount_max_forecast for x in hsname_all_ids)
            purchase_amount_min_forecast_total = sum(x.purchase_amount_min_forecast for x in hsname_all_ids)
            purchase_amount_max_add_forecast_total = sum(x.purchase_amount_max_add_forecast for x in hsname_all_ids)
            purchase_amount_min_add_forecast_total = sum(x.purchase_amount_min_add_forecast for x in hsname_all_ids)
            purchase_amount2_tax_total = sum(x.purchase_amount2_tax for x in hsname_all_ids)
            purchase_amount2_no_tax_total = sum(x.purchase_amount2_no_tax for x in hsname_all_ids)
            purchase_amount2_add_actual_total = sum(x.purchase_amount2_add_actual for x in hsname_all_ids)
            # purchase_back_tax_amount2_new_new_total = sum(x.purchase_back_tax_amount2_new_new for x in hsname_all_ids)
            # purchase_back_tax_amount2_rest_total = sum(x.purchase_back_tax_amount2_rest for x in hsname_all_ids)
            one.purchase_amount_max_forecast_total = purchase_amount_max_forecast_total
            one.purchase_amount_min_forecast_total = purchase_amount_min_forecast_total
            one.purchase_amount_max_add_forecast_total = purchase_amount_max_add_forecast_total
            one.purchase_amount_min_add_forecast_total = purchase_amount_min_add_forecast_total
            one.purchase_amount2_tax_total = purchase_amount2_tax_total
            one.purchase_amount2_no_tax_total = purchase_amount2_no_tax_total
            one.purchase_amount2_add_actual_total = purchase_amount2_add_actual_total
            # one.purchase_back_tax_amount2_new_new_total = purchase_back_tax_amount2_new_new_total
            # one.purchase_back_tax_amount2_rest_total = purchase_back_tax_amount2_rest_total




    comb_ids = fields.One2many('tbl.comb', 'tb_id', u'bom分解组合')
    hsname_ids = fields.One2many('tbl.hsname', 'tb_id', u'HS统计')

    hsname_all_ids = fields.One2many('tbl.hsname.all', 'tb_id', u'报关明细.')#816

    sale_collect_state = fields.Selection([('draft', u'未统计'), ('done', u'已统计')], string=u'销售统计', default='draft')
    tb_po_invoice_ids = fields.One2many('tb.po.invoice','tb_id','增加采购申请单')
    invoice_purchase_po_draft_ids = fields.One2many('account.invoice','bill_id',domain=[('yjzy_type','=','purchase'),('invoice_attribute','=','other_po'),('state','not in',['open','paid'])])
    invoice_purchase_po_done_ids = fields.One2many('account.invoice', 'bill_id', domain=[('yjzy_type', '=', 'purchase'), (
    'invoice_attribute', '=', 'other_po'), ('state', 'in', ['open', 'paid'])])
    invoice_back_tax_po_draft_ids = fields.One2many('account.invoice', 'bill_id', domain=[('yjzy_type', '=', 'back_tax'), (
    'invoice_attribute', '=', 'other_po'), ('state', 'not in', ['open', 'paid'])])
    invoice_back_tax_po_done_ids = fields.One2many('account.invoice', 'bill_id', domain=[('yjzy_type', '=', 'back_tax'), (
        'invoice_attribute', '=', 'other_po'), ('state', 'in', ['open', 'paid'])])
    invoice_sale_po_draft_ids = fields.One2many('account.invoice', 'bill_id',
                                                    domain=[('yjzy_type', '=', 'sale'),
                                                            ('invoice_attribute', '=', 'other_po'),
                                                            ('state', 'not in', ['open', 'paid'])])
    invoice_sale_po_done_ids = fields.One2many('account.invoice', 'bill_id',
                                                   domain=[('yjzy_type', '=', 'sale'), (
                                                       'invoice_attribute', '=', 'other_po'),
                                                           ('state', 'in', ['open', 'paid'])])

    purchase_amount_max_forecast_total = fields.Float('预测采购金额(下限)', digits=(2, 2), compute=_compute_overall_profit)
    purchase_amount_min_forecast_total = fields.Float('预测采购金额(上限)', digits=(2, 2), compute=_compute_overall_profit)
    purchase_amount_max_add_forecast_total = fields.Float('可增加采购额(下限)', digits=(2, 2), compute=_compute_overall_profit)
    purchase_amount_min_add_forecast_total = fields.Float('可增加采购额(上限)', digits=(2, 2), compute=_compute_overall_profit)
    purchase_amount2_tax_total = fields.Float(u'含税采购金额', compute=_compute_overall_profit)
    purchase_amount2_no_tax_total = fields.Float(u'不含税采购金额', compute=_compute_overall_profit)
    purchase_amount2_add_actual_total = fields.Float(U'实际已经增加采购额', compute=_compute_overall_profit)
    # purchase_back_tax_amount2_new_new_total = fields.Float(U'新增退税总金额', compute=_compute_overall_profit)
    # purchase_back_tax_amount2_rest_total = fields.Float(U'可开票退税金额', compute=_compute_overall_profit)
    # 817
    def open_wizard_tb_po_invoice_1(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        ctx.update({
            'default_partner_id': self.partner_id.id,
            'default_hsname_ids': self.hsname_ids
        })
        return {
            'name': u'添加客户',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.tb.po.invoice',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }
    #817定稿
    def open_wizard_tb_po_invoice(self):
        self.ensure_one()
        purchase_invoice_ids = self.purchase_invoice_ids and self.purchase_invoice_ids[0]
        wizard = self.env['wizard.tb.po.invoice'].create({'tb_id': self.id,
                                                          # 'partner_id':self.purchase_invoice_ids[0] and self.purchase_invoice_ids[0].id or False,
                                                          'invoice_product_id': self.env.ref('yjzy_extend.product_qtyfk').id, #0821
                                                          'type':'other_po'
                                                          # 'back_tax_amount':self.purchase_back_tax_amount2_rest_total
                                                          })
        view = self.env.ref('yjzy_extend.wizard_tb_po_form')
        line_obj = self.env['wizard.tb.po.invoice.line']
        for hsl in self.hsname_all_ids:
            line_obj.create({
                'wizard_id': wizard.id,
                'hs_id':hsl.hs_id.id,
                'hs_en_name':hsl.hs_en_name,
                'purchase_amount2_tax':hsl.purchase_amount2_tax,
                'purchase_amount2_no_tax':hsl.purchase_amount2_no_tax,
                'purchase_amount_max_add_forecast':hsl.purchase_amount_max_add_forecast,
                'purchase_amount_min_add_forecast':hsl.purchase_amount_min_add_forecast,
                'purchase_amount_max_add_rest':hsl.purchase_amount_max_add_rest,
                'purchase_amount_min_add_rest':hsl.purchase_amount_min_add_rest,
                'hsname_all_line_id': hsl.id,
                'back_tax':hsl.back_tax
            })

        return {
            'name': _(u'创建采购增加单'),
            'view_type': 'tree,form',
            "view_mode": 'form',
            'res_model': 'wizard.tb.po.invoice',
            'type': 'ir.actions.act_window',
            'view_id': view.id,
            'target': 'new',
            'res_id': wizard.id,
            'context': {'other_po':1,
                        'expense_po':0},
        }

    def open_tb_po_invoice(self):
        self.ensure_one()
        hs_dic={}
        view = self.env.ref('yjzy_extend.tb_po_form')
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'tb.po.invoice',
            'views': [(view.id, 'form')],
            'target': 'current',
            'res_id': self.id,
             'context': {'other_po':1,
                        'expense_po':0},
        }



    # 816 定稿
    def create_hsname_all_ids(self):
        self.ensure_one()
        self.hsname_all_ids.unlink()
        hsname_all_obj = self.env['tbl.hsname.all']
        hs_dic = {}  # {pi*100+soid: }
        for i in self.hsname_ids:
            amount2 = i.amount2
            purchase_amount2 = i.purchase_amount2
            out_qty2 = i.out_qty2
            hs_id = i.hs_id
            is_po_include_tax= i.is_po_include_tax
            back_tax = i.back_tax

            purchase_back_tax_amount2_new = i.purchase_back_tax_amount2_new
            purchase_amount2_tax = i.purchase_amount2_tax
            purchase_amount2_no_tax = i.purchase_amount2_no_tax
            overall_profit_max = i.overall_profit_max
            overall_profit_min = i.overall_profit_min
            purchase_amount_max_forecast = i.purchase_amount_max_forecast
            purchase_amount_min_forecast = i.purchase_amount_min_forecast
            purchase_amount_max_add_forecast = i.purchase_amount_max_add_forecast
            purchase_amount_min_add_forecast = i.purchase_amount_min_add_forecast

            k = hs_id.id


            if k in hs_dic:
                hs_dic[k]['out_qty2'] += out_qty2
                hs_dic[k]['amount2'] += amount2
                hs_dic[k]['purchase_amount2'] += purchase_amount2
                hs_dic[k]['purchase_back_tax_amount2_new'] += purchase_back_tax_amount2_new
                # hs_dic[k]['purchase_amount2_tax'] += purchase_amount2_tax
                # hs_dic[k]['purchase_amount2_no_tax'] += purchase_amount2_no_tax
                # hs_dic[k]['purchase_amount_max_add_forecast'] += purchase_amount_max_add_forecast
                # hs_dic[k]['purchase_amount_min_add_forecast'] += purchase_amount_min_add_forecast
            else:
                hs_dic[k] = {'out_qty2': out_qty2,
                             'amount2': amount2,
                             'purchase_amount2':purchase_amount2,
                             'back_tax':back_tax,
                             'purchase_back_tax_amount2_new':purchase_back_tax_amount2_new,
                             # 'purchase_amount2_tax':purchase_amount2_tax,
                             # 'purchase_amount2_no_tax': purchase_amount2_no_tax,
                             # 'purchase_amount_max_add_forecast':purchase_amount_max_add_forecast,
                             # 'purchase_amount_min_add_forecast':purchase_amount_min_add_forecast,
                             'hs_id': hs_id.id,
                             'overall_profit_max':overall_profit_max,
                             'overall_profit_min':overall_profit_min,
                             'is_po_include_tax':is_po_include_tax}
        for kk, data in list(hs_dic.items()):
            line = hsname_all_obj.create({
                'tb_id': self.id,
                'hs_id': data['hs_id'],
                'out_qty2': data['out_qty2'],
                'amount2': data['amount2'],
                'back_tax':data['back_tax'],
                'purchase_amount2':data['purchase_amount2'],
                'purchase_back_tax_amount2_new': data['purchase_back_tax_amount2_new'],
                # 'purchase_amount2_tax': data['purchase_amount2_tax'],
                # 'purchase_amount2_no_tax': data['purchase_amount2_no_tax'],
                # 'purchase_amount_max_add_forecast': data['purchase_amount_max_add_forecast'],
                # 'purchase_amount_min_add_forecast': data['purchase_amount_min_add_forecast'],
                'overall_profit_max':data['overall_profit_max'],
                'overall_profit_min':data['overall_profit_min'],
                'is_po_include_tax':data['is_po_include_tax'],

                'price': data['amount2'] / (data['out_qty2'] or 1),
            })
            # print('>>', line)




    def test_get_package_tag(self):
        res = self.get_package_tag()
        raise Warning('%s' % res)

    def get_package_tag(self):
        self.ensure_one()
        dic_info = {}
        for line in self.hsname_ids:
            if line.package_tag in dic_info:
                dic_info[line.package_tag]['lines'] |= line
                dic_info[line.package_tag]['qty'] += 1
            else:
                dic_info[line.package_tag] = {'lines': line, 'qty': 1}

        return dic_info

    def get_sale_hs(self, key_name):
        return self.hsname_ids.filtered(lambda x: x.name == key_name)

    def tongji_tbl_hsname(self):
        self.ensure_one()
        res = {}
        for i in self.hsname_ids:
            if i.hs_id in res:
                res[i.hs_id] |= i
            else:
                res[i.hs_id] = i

        print('=======', res)
        return res

    def make_sale_collect(self):
        self.hsname_ids.unlink()
        self.comb_ids.unlink()
        self.make_tbl_comb()
        self.make_tbl_hsname()
        self.hsname_ids.compute_info()
        self.sale_collect_state = 'done'

    def make_tbl_comb(self):
        self.ensure_one()
        comb_obj = self.env['tbl.comb']
        bom_obj = self.env['mrp.bom']

        bom_dic = {}  # {bom:  {tbline: lines, qty: bom_qty}}
        for line in self.line_ids:
            sol = line.sol_id
            so = sol.order_id
            product = line.product_id
            plans = line.lot_plan_ids

            for plan in plans:
                po_id = plan.lot_id.po_id.id

                # 需要合并的
                if sol.bom_id:
                    plan_percent = plan.qty / sol.bom_qty
                    bom = sol.bom_id
                    if sol.bom_id in bom_dic:
                        bom_dic[bom]['tblines'] |= line
                        if bom_dic[bom]['bom_qty'] != sol.bom_qty * plan_percent:
                            raise Warning(u'bom销售数量不一致，请确认')
                    else:
                        bom_dic[bom] = {'tblines': line, 'bom_qty': sol.bom_qty * plan_percent, 'po_id': po_id, 'so_id': so.id}

                # 需要拆分的
                elif sol.need_split_bom:
                    bom = bom_obj._bom_find(product=product)
                    if not bom:
                        raise Warning(u'产品%s没有找到相关的bom信息' % product.defualt_code)
                    lines_done = bom.explode(product, plan.qty)[1]
                    for i in lines_done:
                        # print ('=======需要拆分的=========', i)
                        if not product.lst_price:
                            raise Warning(u'产品%s 没有设置销售价格' % product.default_code)
                        price = i[0].product_id.lst_price * (sol.price_unit / product.lst_price)

                        amount = line.org_currency_sale_amount * i[0].price_percent * (plan.qty / line.qty2stage)

                        comb_obj.create({
                            'tb_id': self.id,
                            'tbl_id': line.id,
                            'product_id': i[0].product_id.id,
                            'out_qty': i[1]['qty'],
                            'price': amount / i[1]['qty'],  # price,
                            'amount': amount,  # i[1]['qty'] * price,
                            'po_id': po_id,
                            'so_id': so.id,
                            'note': '销售金额%s  bom百分比%s  计划数量%s  销售数量%s   = 最终金额 %s ' % (
                                line.org_currency_sale_amount, i[0].price_percent, plan.qty, line.qty2stage, amount)
                        })
                # 正常的
                else:
                    price_a = line.org_currency_sale_amount / line.qty2stage
                    comb_obj.create({
                        'tb_id': self.id,
                        'tbl_id': line.id,
                        'product_id': line.product_id.id,
                        'out_qty': plan.qty,
                        'price': price_a,
                        'amount': plan.qty * price_a,
                        'po_id': po_id,
                        'so_id': so.id,
                    })

        # 创建bom产品
        # print('>>>>>>>>>>', bom_dic)
        for bom, info in bom_dic.items():
            tblines = info['tblines']
            amount = sum(tblines.mapped('org_currency_sale_amount'))
            # print('>>>>>>>>>>2', bom.product_id)
            comb_obj.create({
                'tb_id': self.id,
                'product_id': bom.product_id.id or bom.product_tmpl_id.product_variant_ids[0].id,
                'out_qty': info['bom_qty'],
                'price': amount / info['bom_qty'],
                'amount': amount,
                'po_id': info['po_id'],
                'so_id': info['so_id',]
            })

    def make_tbl_hsname(self):
        obj = self.env['tbl.hsname']
        hs_dic = {}  # {'hs_name': {'dump_product': product, }}
        for one in self.comb_ids:
            hs = one.hs_id
            key_name = '%s:%s' % (hs.id, one.po_id.id)
            # print('====make_tbl_hsname====', hs)
            if key_name not in hs_dic:
                hs_dic[key_name] = {'dump_product': one.product_id, 'comb_lines': one, 'out_qty': one.out_qty, 'hs_id': hs.id, 'po_id': one.po_id.id}
            else:
                hs_dic[key_name]['comb_lines'] |= one
                hs_dic[key_name]['out_qty'] += one.out_qty

        for key_name, info in hs_dic.items():
            # print('>>>info', info)
            comb_lines = info['comb_lines']
            amount = sum(comb_lines.mapped('amount'))
            out_qty = sum(comb_lines.mapped('out_qty'))
            record = obj.create({
                'name': key_name,
                'hs_id': info['hs_id'],
                'po_id': info['po_id'],
                'dump_product_id': info['dump_product'].id,
                'price': amount / out_qty,
                'amount': amount,
                'out_qty': out_qty,
                'tb_id': self.id,
            })
            record.comb_ids = info['comb_lines']


class tbl_comb(models.Model):
    _name = 'tbl.comb'
    _description = u'发运单明细的bom分解组合'

    tbl_id = fields.Many2one('transport.bill.line', u'发运明细')
    tb_id = fields.Many2one('transport.bill', u'发运')
    product_id = fields.Many2one('product.product', u'产品')
    hs_id = fields.Many2one('hs.hs', u'HS', related='product_id.hs_id')
    out_qty = fields.Float('发运数量')
    in_qty = fields.Float('IN QTY')
    price = fields.Float('单价')
    amount = fields.Float('金额')
    po_id = fields.Many2one('purchase.order', u'采购单')
    tbl_hsname_id = fields.Many2one('tbl.hsname', 'HS统计')
    so_id = fields.Many2one('sale.order', u'销售订单')
    note = fields.Text(u'备注')


class tbl_hsname(models.Model):
    _name = 'tbl.hsname'
    _description = u'发运HS统计'
    _rec_name = 'name'

    @api.depends('dump_product_id', 'comb_ids')
    def compute_info(self):
        for one in self:
            pdt = one.dump_product_id
            one.source_area = pdt.source_area
            one.source_country_id = pdt.source_country_id

            x = {'max_qty': 0, 'mid_qty': 0, 'min_qty': 0, 'gross_weight': 0, 'net_weight': 0, 'volume': 0}
            for comb in one.comb_ids:
                i = comb.product_id.get_package_info(comb.out_qty)
                x['max_qty'] += i['max_qty']
                x['mid_qty'] += i['mid_qty']
                x['min_qty'] += i['min_qty']
                x['gross_weight'] += i['gross_weight']
                x['net_weight'] += i['net_weight']
                x['volume'] += i['volume']

            # x = pdt.get_package_info(one.out_qty)
            one.qty_max = x['max_qty']
            one.qty_mid = x['mid_qty']
            one.qty_min = x['min_qty']
            one.gross_weight = x['gross_weight']
            one.net_weight = x['net_weight']
            one.volume = x['volume']

    @api.depends('amount2', 'out_qty2')
    def compute_price2(self):
        for one in self:
            if one.out_qty2 != 0:
                one.price2 = one.amount2 / one.out_qty2
            else:
                one.price2 = 0

    def compute_shiji(self):
        for one in self:
            one.shiji_weight = one.gross_weight + one.tuopan_weight
            one.shiji_volume = one.volume + one.tuopan_volume
    #814  后面要结合采购报关金额来处理
    def _get_overall_profit(self):
        for one in self:
            overall_profit_max = float(self.env['ir.config_parameter'].sudo().get_param('addons_yjzy.overall_profit_max'))
            overall_profit_min = float(self.env['ir.config_parameter'].sudo().get_param('addons_yjzy.overall_profit_min'))
            declare_amount = one.amount2
            current_date_rate = one.tb_id.current_date_rate
            purchase_amount = one.purchase_amount
            back_tax = one.back_tax
            purchase_amount_max_forecast = (1 - overall_profit_max) * declare_amount * current_date_rate * 1.13 / (1.13 - back_tax)
            purchase_amount_min_forecast = (1 - overall_profit_min) * declare_amount * current_date_rate * 1.13 / (1.13 - back_tax)
            if one.is_po_include_tax:
                purchase_amount_max_add_forecast = purchase_amount_max_forecast - purchase_amount
                purchase_amount_min_add_forecast = purchase_amount_min_forecast - purchase_amount
            else:
                purchase_amount_max_add_forecast = purchase_amount_max_forecast
                purchase_amount_min_add_forecast = purchase_amount_min_forecast
            print('overall_profit',overall_profit_max,overall_profit_min,purchase_amount_max_forecast)
            one.overall_profit_max = overall_profit_max
            one.overall_profit_min = overall_profit_min
            one.purchase_amount_max_forecast = purchase_amount_max_forecast
            one.purchase_amount_min_forecast = purchase_amount_min_forecast
            one.purchase_amount_max_add_forecast = purchase_amount_max_add_forecast
            one.purchase_amount_min_add_forecast = purchase_amount_min_add_forecast
    @api.depends('amount2')
    def compute_purchase_amount(self):
        for one in self:
            if one.is_po_include_tax:
                one.purchase_amount2_tax = one.purchase_amount2
                one.purchase_amount2_no_tax = 0.0
            else:
                one.purchase_amount2_tax = 0.0
                one.purchase_amount2_no_tax = one.purchase_amount2

    #820
    # tax_change = fields.Selection([('no_tax_to_tax','未税转含税'),('tax_to_no_tax','含税转未税')],'含税状态变化')

    #816

    # invoice_hs_line_ids = fields.One2many('invoice.hs_name.item','tb_hsname_line_id', '报关开票明细') #817


    #akiny新增 814
    is_po_include_tax = fields.Boolean(u'采购是否含税',related='po_id.include_tax', readonly=False)
    overall_profit_max = fields.Float('综合利润率(下限)', digits=(2, 2),compute=_get_overall_profit)#default=lambda self:self.env['ir.config_parameter'].sudo().get_param('addons_yjzy.overall_profit_max')
    overall_profit_min = fields.Float('综合利润率(上限)', digits=(2, 2),compute=_get_overall_profit)#default=lambda self:self.env['ir.config_parameter'].sudo().get_param('addons_yjzy.overall_profit_min')
    purchase_amount_max_forecast = fields.Float('预测采购金额(下限)', digits=(2, 2),compute=_get_overall_profit)
    purchase_amount_min_forecast = fields.Float('预测采购金额(上限)', digits=(2, 2), compute=_get_overall_profit)
    purchase_amount_max_add_forecast = fields.Float('可增加采购额(下限)', digits=(2, 2), compute=_get_overall_profit)
    purchase_amount_min_add_forecast = fields.Float('可增加采购额(上限)', digits=(2, 2), compute=_get_overall_profit)
    purchase_amount2_tax = fields.Float(u'含税采购金额', compute=compute_purchase_amount)
    purchase_amount2_no_tax = fields.Float(u'不含税采购金额', compute=compute_purchase_amount)

    name = fields.Char('HS:PO')
    tb_id = fields.Many2one('transport.bill', u'发运', ondelete='cascade')
    hs_id = fields.Many2one('hs.hs', u'品名')
    po_id = fields.Many2one('purchase.order', u'采购单')
    hs_en_name = fields.Char(related='hs_id.en_name')
    back_tax = fields.Float(related='hs_id.back_tax')

    dump_product_id = fields.Many2one('product.product', u'产品')
    out_qty = fields.Float('数量')
    price = fields.Float('价格')
    amount = fields.Float('金额', digits=dp.get_precision('Money'))
    comb_ids = fields.One2many('tbl.comb', 'tbl_hsname_id', u'分解明细')

    hs_id2 = fields.Many2one('hs.hs', u'报关品名')
    dump_product_id2 = fields.Many2one('product.product', u'报关产品')
    out_qty2 = fields.Float('报关数量')
    price2 = fields.Float('报关价格', compute=compute_price2)
    amount2 = fields.Float('报关金额', digits=dp.get_precision('Money'))

    source_area = fields.Char(u'原产地')
    source_country_id = fields.Many2one('res.country', u'原产国')
    qty_max = fields.Integer(u'大包装件数')
    qty_mid = fields.Integer(u'中包装件数')
    qty_min = fields.Integer(u'小包装件数')
    gross_weight = fields.Float(u'毛重', digits=dp.get_precision('Weight'))
    net_weight = fields.Float(u'净重', digits=dp.get_precision('Weight'))
    volume = fields.Float(u'尺码m³', digits=dp.get_precision('Volume'))
    keyword = fields.Char(u'报关要素')
    type = fields.Selection([('auto', u'自动'), ('manual', '手动')], u'创建方式', default='auto')
    note = fields.Char(u'其他')

    tuopan_weight = fields.Float(u'托盘分配重量', digits=dp.get_precision('Weight'))
    tuopan_volume = fields.Float(u'托盘分配体积', digits=dp.get_precision('Volume'))

    shiji_weight = fields.Float(u'实际毛重', compute=compute_shiji, digits=dp.get_precision('Weight'))
    shiji_volume = fields.Float(u'实际体积', compute=compute_shiji, digits=dp.get_precision('Volume'))

    package_tag = fields.Char('包裹标记')

    suppliser_hs_amount = fields.Float('采购HS统计金额')

    # 销售hs统计同步采购hs统计
    purchase_hs_id = fields.Many2one('btls.hs', '采购HS统计')
    purchase_amount = fields.Float('采购金额', related="purchase_hs_id.amount")
    purchase_amount2 = fields.Float('采购金额', related="purchase_hs_id.amount2") #814需要优化
    purchase_back_tax_amount2 = fields.Float(u'报关退税金额',related="purchase_hs_id.back_tax_amount2")
    purchase_back_tax_amount2_new = fields.Float(u'报关退税金额：新',related="purchase_hs_id.back_tax_amount2_new")








    #可以删除
    # def open_wizard_tb_po_invoice(self):
    #     self.ensure_one()
    #     wizard = self.env['wizard.tb.po.invoice'].create({'hsmane_id': self.id})
    #
    #     return {
    #         'name': u'添加客户',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'wizard.tb.po.invoice',
    #         'res_id': wizard.id,
    #         'type': 'ir.actions.act_window',
    #         'target': 'new',
    #
    #     }


    def open_form_view(self):
        return {
            'name': '发运HS统计',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self._name,
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }


    @api.multi
    def write(self, vals):
        res = super(tbl_hsname, self).write(vals)
        need = set(['hs_id', 'hs_id2', 'out_qty', 'out_qty2', 'po_id']) & set(vals.keys())
        if need:
            self.sync_purhcse_hs()
        return res


    def sync_purhcse_hs(self):
        for one in self:
            purchase_hs = one.purchase_hs_id
            if purchase_hs:
                purchase_hs.hs_id = one.hs_id
                purchase_hs.hs_id2 = one.hs_id2
                purchase_hs.qty = one.out_qty
                purchase_hs.qty2 = one.out_qty2
                purchase_hs.po_id = one.po_id
                purchase_hs.supplier_id = one.po_id.partner_id.id,
               # purchase_hs.amount = one.amount
               #  purchase_hs.amount2 = one.amount2


    @api.onchange('hs_id')
    def onchange_hs(self):
        self.hs_id2 = self.hs_id

    @api.model
    def create(self, vals):
        one = super(tbl_hsname, self).create(vals)
        one.hs_id2 = one.hs_id
        one.dump_product_id2 = one.dump_product_id
        one.out_qty2 = one.out_qty
        one.price2 = one.price
        one.amount2 = one.amount
        return one

    def make_suppliser_hs(self):
        suppliser_hs_obj = self.env['btls.hs']
        suppliser_hs_record = self.purchase_hs_id or suppliser_hs_obj.search([('sale_hs_id', '=', self.id)])

        if not suppliser_hs_record:
            suppliser_hs_record = suppliser_hs_obj.create({
                'sale_hs_id': self.id,
                'amount': self.suppliser_hs_amount,
                'tb_id': self.tb_id.id,
                'qty': self.out_qty,
                'price': 1,
                'hs_id': self.hs_id.id,
                'po_id': self.po_id.id,
                'supplier_id': self.po_id.partner_id.id,
            })
            self.purchase_hs_id = suppliser_hs_record
            self.sync_purhcse_hs()

#816
class tbl_hsname_all(models.Model):
    _name = 'tbl.hsname.all'
    _description = u'采购金额统计'
    # _rec_name = 'name'

    def compute_info(self):
        for one in self:
            inv_hs_name_line_po_ids = one.inv_hs_name_line_ids.filtered(lambda x: x.invoice_id.yjzy_type == 'purchase')
            # inv_hs_name_line_back_tax_ids = one.inv_hs_name_line_ids.filtered(lambda x: x.invoice_id.yjzy_type == 'back_tax')
            # inv_hs_name_line_sale_ids = one.inv_hs_name_line_ids.filtered(
            #     lambda x: x.invoice_id.yjzy_type == 'sale')
            purchase_amount2_add_actual = sum(x.purchase_amount2_add_this_time for x in inv_hs_name_line_po_ids)
            back_tax_add_actual = sum(x.back_tax_add_this_time for x in inv_hs_name_line_po_ids)
            p_s_add_actual = sum(x.p_s_add_this_time for x in inv_hs_name_line_po_ids)
            #purchase_back_tax_amount2_actual = purchase_amount2_add_actual / 1.13 * one.back_tax



            # purchase_amount_max_add_forecast = one.purchase_amount_max_add_forecast
            # purchase_amount_min_add_forecast = one.purchase_amount_min_add_forecast
            # back_tax_amount_new = one.purchase_back_tax_amount2_new
            overall_profit_max = one.overall_profit_max
            overall_profit_min = one.overall_profit_min
            declare_amount = one.amount2
            current_date_rate = one.tb_id.current_date_rate
            back_tax = one.back_tax
            purchase_amount_max_forecast = (1 - overall_profit_max) * declare_amount * current_date_rate * 1.13 / (1.13 - back_tax)
            purchase_amount_min_forecast = (1 - overall_profit_min) * declare_amount * current_date_rate * 1.13 / (1.13 - back_tax)
            purchase_amount2 = one.purchase_amount2


            if one.is_po_include_tax:
                purchase_amount2_tax = purchase_amount2
                purchase_amount2_no_tax = 0.0
                purchase_amount_max_add_forecast = purchase_amount_max_forecast - purchase_amount2
                purchase_amount_min_add_forecast = purchase_amount_min_forecast - purchase_amount2
                #back_tax_amount_new_new = one.purchase_amount2 / 1.13 * one.back_tax - back_tax_amount_new #总的实际的应该另外创建的退税金额

            else:
                purchase_amount2_tax = 0.0
                purchase_amount2_no_tax = purchase_amount2
                #back_tax_amount_new_new = 0.0
                purchase_amount_max_add_forecast = purchase_amount_max_forecast
                purchase_amount_min_add_forecast = purchase_amount_min_forecast
            purchase_amount_max_add_rest = purchase_amount_max_add_forecast - purchase_amount2_add_actual
            purchase_amount_min_add_rest = purchase_amount_min_add_forecast - purchase_amount2_add_actual


            one.purchase_amount2_add_actual = purchase_amount2_add_actual
            one.back_tax_add_actual = back_tax_add_actual
            one.p_s_add_actual = p_s_add_actual
            one.purchase_amount_max_add_rest = purchase_amount_max_add_rest
            one.purchase_amount_min_add_rest = purchase_amount_min_add_rest
            one.purchase_amount2_tax = purchase_amount2_tax
            one.purchase_amount2_no_tax = purchase_amount2_no_tax
            one.purchase_amount_max_forecast = purchase_amount_max_forecast
            one.purchase_amount_min_forecast = purchase_amount_min_forecast
            one.purchase_amount_max_add_forecast = purchase_amount_max_add_forecast
            one.purchase_amount_min_add_forecast = purchase_amount_min_add_forecast
            # one.purchase_back_tax_amount2_new_new = back_tax_amount_new_new
            # one.purchase_back_tax_amount2_rest = back_tax_amount_new_new - purchase_back_tax_amount2_actual

    #817
    tb_id = fields.Many2one('transport.bill', u'出运单', ondelete='cascade')
    hs_id = fields.Many2one('hs.hs', u'品名')
    inv_hs_name_line_ids = fields.One2many('invoice.hs_name.all','tbl_hsname_all_id','发票对应明细') #关联发票的报关汇总明细
    purchase_amount2_add_actual = fields.Float(U'实际已经增加采购额', compute=compute_info)
    back_tax_add_actual = fields.Float(U'实际已经增加退税', compute=compute_info)
    p_s_add_actual = fields.Float(U'实际已经增加应收', compute=compute_info)


    hs_en_name = fields.Char(related='hs_id.en_name')
    # akinyback
    # back_tax = fields.Float(related='hs_id.back_tax')
    back_tax = fields.Float(u'退税率', digits=dp.get_precision('Back Tax'))

    hs_id2 = fields.Many2one('hs.hs', u'报关品名')
    out_qty2 = fields.Float('报关数量')
    price2 = fields.Float('报关价格',)
    amount2 = fields.Float('报关金额', digits=dp.get_precision('Money'))


    suppliser_hs_amount = fields.Float('采购HS统计金额')

    # 销售hs统计同步采购hs统计
    purchase_amount2 = fields.Float('采购金额')  # 814需要优化
    purchase_back_tax_amount2 = fields.Float(u'报关退税税金额')
    purchase_back_tax_amount2_new = fields.Float(u'原始退税金额')#根据是否含税来进行计算
    # purchase_back_tax_amount2_new_new = fields.Float(u'预计退税总金额',compute=compute_info)#根据是否含税来进行计算
    purchase_amount2_tax = fields.Float(u'含税采购额',compute=compute_info)
    purchase_amount2_no_tax = fields.Float(u'不含税采购额',compute=compute_info)


    purchase_amount2_add_this_time = fields.Float(U'本次采购开票金额')

    is_po_include_tax = fields.Boolean(u'采购是否含税')


    overall_profit_max = fields.Float('综合利润率(下限)', digits=(2, 2)
                                      )  # default=lambda self:self.env['ir.config_parameter'].sudo().get_param('addons_yjzy.overall_profit_max')
    overall_profit_min = fields.Float('综合利润率(上限)', digits=(2, 2)
                                      )  # default=lambda self:self.env['ir.config_parameter'].sudo().get_param('addons_yjzy.overall_profit_min')
    purchase_amount_max_forecast = fields.Float('预测采购额(下限)', digits=(2, 2),compute=compute_info)
    purchase_amount_min_forecast = fields.Float('预测采购额(上限)', digits=(2, 2),compute=compute_info)
    purchase_amount_max_add_forecast = fields.Float('可增加采购额(下限)', digits=(2, 2),compute=compute_info)
    purchase_amount_min_add_forecast = fields.Float('可增加采购额(上限)', digits=(2, 2),compute=compute_info)
    purchase_amount_max_add_rest = fields.Float('采购池(下限)', digits=(2, 2),compute=compute_info)
    purchase_amount_min_add_rest = fields.Float('采购池(上限)', digits=(2, 2),compute=compute_info)
    # purchase_back_tax_amount2_rest = fields.Float('本次退税金额', digits=(2, 2),compute=compute_info)


