# -*- coding: utf-8 -*-
from num2words import num2words
from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning
from .comm import BACK_TAX_RATIO


class transport_bill(models.Model):
    _inherit = 'transport.bill'

    btl_supplier_ids = fields.One2many('btl.supplier', 'tb_id', u'供应商明细')
    btls_comb_ids = fields.One2many('btls.comb', 'tb_id', u'供应商明细BOM分解组合')
    btls_hs_ids = fields.One2many('btls.hs', 'tb_id', u'供应商明细HS统计')
    purchase_collect_state = fields.Selection([('draft', u'未统计'), ('done', u'已统计')], string=u'采购统计', default='draft')

    fandian_ids = fields.One2many('transport.bill.fandian', 'tb_id', u'返点明细')

    def create_btls_hs_ids_purchase(self):#采购发票的进项hs明细

        btls_hs_dic = {}  # key= hs_id*supplier*po.id
        for one in self.btls_hs_ids:
            partner = one.supplier_id.id
            purchase_invoice_id = self.purchase_invoice_ids.filtered(lambda x: x.partner_id == one.supplier_id)
            if partner in btls_hs_dic:
                btls_hs_dic[partner]['qty2'] += one.qty2
                btls_hs_dic[partner]['amount2'] += one.amount2
                btls_hs_dic[partner]['back_tax_amount2'] += one.back_tax_amount2_new
            else:
                btls_hs_dic[partner] = {'partner': one.supplier_id,'invoice_id':purchase_invoice_id,'back_tax_amount2':one.back_tax_amount2_new, 'hs': one.hs_id2, 'qty2': one.qty2, 'amount2':one.amount2,'price2':one.price2}
        pih_obj = self.env['purchase.invoice.hsname']
        for partner, v in btls_hs_dic.items():
            purchase_hs = pih_obj.create({
                'partner_id': v['partner'].id,
                'qty2': v['qty2'],
                'price2':v['price2'],
                'amount2': v['amount2'],
                'invoice_id':v['invoice_id'].id,
                'hs_id': v['hs'].id,
                'back_tax_amount2':v['back_tax_amount2']
            })



    def tongji_btls_by_po(self):
        self.ensure_one()
        res = {}
        for line in self.btls_hs_ids:
            if line.po_id in res:
                res[line.po_id] |= line
            else:
                res[line.po_id] = line
        return res


    def get_group_hs_lines(self):
        self.ensure_one()
        # group by hs
        res = {}  # {hs, lines}
        for line in self.btls_hs_ids:
            hs = line.hs_id
            if hs in res:
                res[hs] |= line
            else:
                res[hs] = line

        return res

    def get_group_partner_lines(self):
        self.ensure_one()
        # group by hs
        res = {}  # {hs, lines}
        for line in self.btls_hs_ids:
            hs = line.hs_id
            partner = line.supplier_id
            k = '%s:%s:%s' % (hs.id, partner.id, line.tongji_type)
            if k in res:
                res[k] |= line
            else:
                res[k] = line

        return res

    def make_purchase_collect(self):
        if self.sale_collect_state != 'done':
            raise Warning(u'请先做销售统计')

        self.btls_hs_ids.unlink()
        self.btls_comb_ids.unlink()
        self.btl_supplier_ids.unlink()

        self.make_btl_supplier()
        self.make_tbls_comb()
        self.make_btls_hs()
        self.relation_hs_purchase_sale()

        self.purchase_collect_state = 'done'

    def make_btl_supplier(self):
        self.btl_supplier_ids.unlink()
        tbls_obj = self.env['btl.supplier']
        for line in self.line_ids:
            for plan in line.lot_plan_ids:
                tongji_type = plan.stage_1 and 'purchase' or 'stock'
                po = plan.lot_id.po_id
                tbls_obj.create({
                    'tbl_id': line.id,
                    'lot_plan_id': plan.id,
                    'qty': plan.qty,
                    'tongji_type': tongji_type,
                    'need_purchase_fandian': po.need_purchase_fandian,
                    'purchase_fandian_ratio': po.purchase_fandian_ratio,
                    'purchase_fandian_partner_id': po.purchase_fandian_partner_id.id,
                })

    def make_tbls_comb(self):
        self.btls_comb_ids.unlink()
        self.ensure_one()
        comb_obj = self.env['btls.comb']
        bom_obj = self.env['mrp.bom']
        bom_dic = {}  # {bom:  {tbline: lines, qty: bom_qty}}
        for line in self.btl_supplier_ids:
            tbl = line.tbl_id
            sol = line.sol_id
            product = line.product_id
            # 需要合并的
            if sol.bom_id:
                # 是bom散件的明细，收集到bom字典后续创建
                bom = sol.bom_id
                bom_qty = line.qty * sol.bom_qty / sol.product_uom_qty
                if sol.bom_id in bom_dic:
                    bom_dic[bom]['tblines'] |= line
                    bom_dic[bom]['amount'] += line.amount
                else:
                    bom_dic[bom] = {'tblines': line, 'bom_qty': bom_qty, 'amount': line.amount, 'supplier': line.supplier_id, 'tongji_type': line.tongji_type,}
            # 需要拆分的
            elif sol.need_split_bom:
                bom = bom_obj._bom_find(product=product)
                if not bom:
                    raise Warning(u'产品%s没有找到相关的bom信息' % product.defualt_code)
                lines_done = bom.explode(product, line.qty)[1]
                for i in lines_done:
                    if not product.lst_price:
                        raise Warning(u'产品%s 没有设置销售价格' % product.default_code)

                    amount = line.amount * i[0].price_percent
                    qty = i[1]['qty']
                    comb_obj.create({
                        'tb_id': self.id,
                        'product_id': i[0].product_id.id,
                        'qty': qty,
                        'price': amount / i[1]['qty'],
                        'amount': amount,
                        'supplier_id': line.supplier_id.id,
                        'po_id': line.po_id.id,
                        'tongji_type': line.tongji_type,
                    })
            # 正常的
            else:
                comb_obj.create({
                    'tb_id': self.id,
                    'tbl_id': tbl.id,
                    'product_id': line.product_id.id,
                    'qty': line.qty,
                    'price': line.price,
                    'amount': line.amount,
                    'supplier_id': line.supplier_id.id,
                    'po_id': line.po_id.id,
                    'tongji_type': line.tongji_type,
                })
        for bom, v in bom_dic.items():
            comb_obj.create({
                'tb_id': self.id,
                # 'tbl_id': tbl.id,
                'product_id': bom.product_id.id or bom.product_tmpl_id.product_variant_ids[0].id,
                'qty': v['bom_qty'],
                'amount': v['amount'],
                'price': v['amount'] / v['bom_qty'],
                'supplier_id': v['supplier'].id,
                'tongji_type': v['tongji_type'],
            })

    def make_btls_hs(self):
        self.btls_hs_ids.unlink()

        hs_obj = self.env['btls.hs']

        hs_dic = {}  # key= hs_id*supplier*po.id
        for comb in self.btls_comb_ids:
            # k = comb.po_id.id * 1000000 + comb.supplier_id.id * 1000 + comb.hs_id.id
            key_name = '%s:%s:%s' % (comb.hs_id.id, comb.po_id.id, comb.tongji_type)

            sale_hs_name = '%s:%s' % (comb.hs_id.id, comb.po_id.id)

            sale_hs = self.get_sale_hs(sale_hs_name)
            sale_hs_id = sale_hs and sale_hs.id or False

            # print(k, comb.supplier_id, comb.hs_id)
            if key_name in hs_dic:
                hs_dic[key_name]['qty'] += comb.qty
                hs_dic[key_name]['combs'] |= comb
                hs_dic[key_name]['amount'] += comb.amount
            else:
                hs_dic[key_name] = {'product': comb.product_id, 'hs': comb.hs_id, 'qty': comb.qty, 'combs': comb, 'amount': comb.amount,
                                    'supplier': comb.supplier_id, 'po': comb.po_id, 'tongji_type': comb.tongji_type, 'sale_hs_id': sale_hs_id}

        sale_hs_obj = self.env['tbl.hsname']
        for key_name, v in hs_dic.items():
            purchase_hs = hs_obj.create({
                'name': key_name,
                'tb_id': self.id,
                'product_id': v['product'].id,
                'qty': v['qty'],
                'price': v['amount'] / v['qty'],
                'amount': v['amount'],
                'supplier_id': v['supplier'].id,
                # 'hs_id': v['hs'].id, #这里一写进去 就会报不同公司的权限错误，原因还没找到
                # 'hs_id2': v['hs'].id,
                'po_id': v['po'].id,
                'tongji_type': v['tongji_type'],
                'sale_hs_id': v['sale_hs_id'],

                # 'tb_id2': self.id,
                # 'product_id2': v['product'].id,
                # 'qty2': v['qty'],
                # 'price2': v['amount'] / v['qty'],
                # 'amount2': v['amount'],
                # 'back_tax2': v['hs'].back_tax,
                # 'back_tax_amount2': 0,

            })
            purchase_hs.write({'hs_id' : v['hs'].id,
                               'hs_id2': v['hs'].id,
                               })
            sale_hs_obj.browse(v['sale_hs_id']).purchase_hs_id = purchase_hs



    def relation_hs_purchase_sale(self):
        for po_line in self.btls_hs_ids:
            for so_line in self.hsname_ids:
                if po_line.name == so_line.name:
                    po_line.sale_hs_id = so_line

    def make_fandian_collect(self):
        self.fandian_ids.unlink()
        fandian_obj = self.env['transport.bill.fandian']

        dic_fandian = {}  #{partner, {'lines':, 'supplier'}}
        for i in self.btl_supplier_ids.filtered(lambda x: x.need_purchase_fandian):

            if i.purchase_fandian_partner_id in dic_fandian:
                dic_fandian[i.purchase_fandian_partner_id]['lines'] |= i
            else:
                dic_fandian[i.purchase_fandian_partner_id] = {'lines': i, 'supplier': i.supplier_id}

        for partner, info in dic_fandian.items():
            purchase_amout = sum([x.amount for x in info['lines']])
            if self.include_tax:
                fandian_amount = sum([x.amount / 1.12 * x.purchase_fandian_ratio/100  for x in info['lines']])
            else:
                fandian_amount = sum([x.amount * x.purchase_fandian_ratio/100 for x in info['lines']])

            fandian_obj.create({
                'tb_id': self.id,
                'partner_id': partner.id,
                'supplier_id': info['supplier'].id,
                'purchase_amout': purchase_amout,
                'fandian_amount': fandian_amount,
            })

        return True




class btl_supplier(models.Model):
    _name = 'btl.supplier'
    _description = u'出运供应商明细'

    def compute_amount(self):
        for one in self:
            one.amount = one.qty * one.price

    tbl_id = fields.Many2one('transport.bill.line', u'发运明细', ondelete='cascade')
    sol_id = fields.Many2one('sale.order.line', related='tbl_id.sol_id')
    tb_id = fields.Many2one('transport.bill', related='tbl_id.bill_id', store=True)
    product_id = fields.Many2one('product.product', related='tbl_id.product_id')

    lot_plan_id = fields.Many2one('transport.lot.plan', u'入库调拨计划')
    lot_id = fields.Many2one('stock.production.lot', related='lot_plan_id.lot_id')
    po_id = fields.Many2one('purchase.order', related='lot_id.po_id')

    need_purchase_fandian = fields.Boolean(u'采购返点')
    purchase_fandian_ratio = fields.Float(u'返点比例：%')
    purchase_fandian_partner_id = fields.Many2one('res.partner', u'返点对象')

    supplier_id = fields.Many2one('res.partner', related='po_id.partner_id', string=u'供应商')
    qty = fields.Float(related='lot_plan_id.qty')
    price = fields.Float(related='lot_id.purchase_price')
    amount = fields.Float('金额', compute='compute_amount')

    tongji_type = fields.Selection([('purchase', u'采购'), ('stock', u'库存')], u'统计类型')


class btls_comb(models.Model):
    _name = 'btls.comb'
    _description = u'供应商明细BOM分解组合'

    tb_id = fields.Many2one('transport.bill', u'发运', ondelete='cascade')
    product_id = fields.Many2one('product.product', u'产品')
    hs_id = fields.Many2one('hs.hs', related='product_id.hs_id', string=u'品名')
    qty = fields.Float('数量')
    price = fields.Float('单价')
    amount = fields.Float('金额')
    supplier_id = fields.Many2one('res.partner', u'供应商')
    po_id = fields.Many2one('purchase.order', u'采购单')
    tongji_type = fields.Selection([('purchase', u'采购'), ('stock', u'库存')], u'统计类型')


class btls_hs(models.Model):
    _name = 'btls.hs'
    _description = u'供应商明细HS统计'

    @api.depends('amount2', 'qty2')
    def compute_price2(self):
        for one in self:
            if one.qty2 != 0:
                one.price2 = one.amount2 / one.qty2
            else:
                one.price2 = 0
            if one.tb_id.cip_type != 'normal':
                back_tax_amount = 0
            else:
                back_tax_amount = one.amount2 / 1.13 * one.back_tax
            if one.po_id.include_tax:
                back_tax_amount_new = one.amount2 / 1.13 * one.back_tax
            else:
                back_tax_amount_new = 0

            one.back_tax_amount2 = back_tax_amount
            one.back_tax_amount2_new = back_tax_amount_new

    name = fields.Char('HS:PO')
    tb_id = fields.Many2one('transport.bill', u'发运', ondelete='cascade')
    hs_en_name = fields.Char(related='hs_id.en_name',)
    sale_hs_id = fields.Many2one('tbl.hsname', u'销售HS统计', ondelete="cascade")
    sale_hs_db_id = fields.Integer(related='sale_hs_id.id', readonly=True, string=u'销售HS统计ID')
    supplier_id = fields.Many2one('res.partner', u'供应商')
    po_id = fields.Many2one('purchase.order', u'采购单')
    is_po_include_tax = fields.Boolean(u'采购是否含税',related='po_id.include_tax', readonly=False)
    po_code = fields.Char(u'采购合同', related='po_id.contract_code')


    hs_id = fields.Many2one('hs.hs', string=u'品名')
    product_id = fields.Many2one('product.product', u'产品')
    qty = fields.Float('数量')
    price = fields.Float('单价')
    amount = fields.Float('原始采购金额', digits=dp.get_precision('Money'))
    #akinyback_tax
    back_tax = fields.Float(related='hs_id.back_tax')
    back_tax_amount = fields.Float(u'退税金额', digits=dp.get_precision('Money'))

    hs_id2 = fields.Many2one('hs.hs', string=u'报关品名')
    product_id2 = fields.Many2one('product.product', u'报关产品')
    qty2 = fields.Float(u'报关数量')
    price2 = fields.Float(u'报关单价')
    amount2 = fields.Float(u'实际采购金额', digits=dp.get_precision('Money'))
    actual_purchase_amount = fields.Float('实际采购金额', )  #   #暂时不用
    back_tax2 = fields.Float(related='hs_id2.back_tax')
    back_tax_amount2 = fields.Float(u'报关退税金额', compute=compute_price2, digits=dp.get_precision('Money'))
    back_tax_amount2_new = fields.Float(u'报关退税金额', compute=compute_price2, digits=dp.get_precision('Money'))
    actual_purchase_back_tax_amount = fields.Float('实际退税金额')  # 暂时不用
    tongji_type = fields.Selection([('purchase', u'采购'), ('stock', u'库存')], u'统计类型')

    @api.onchange('po_id')
    def onchange_po(self):
        self.supplier_id = self.po_id.partner_id

    @api.model
    def create(self, vals):
        one = super(btls_hs, self).create(vals)
        if one.tb_id.cip_type != 'normal':
            back_tax_amount = 0
        else:
            back_tax_amount = one.amount / BACK_TAX_RATIO * one.back_tax

        one.back_tax_amount = back_tax_amount
        one.hs_id2 = one.hs_id
        one.product_id2 = one.product_id
        one.qty2 = one.qty
        one.price2 = one.price
        one.amount2 = one.amount
        one.back_tax2 = one.back_tax
        one.back_tax_amount2 = back_tax_amount
        # one.actual_purchase_amount = one.amount#暂时不用
        one.actual_purchase_back_tax_amount = one.back_tax#暂时不用
        return one






