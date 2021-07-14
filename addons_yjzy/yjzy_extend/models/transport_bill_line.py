
# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning
from . comm import BACK_TAX_RATIO

Stage_Status = [
    ('draft', u'未开始'),
    ('confirmed', u'就绪'),
    ('done', u'完成'),
]
Stage_Status_Default = 'draft'


class transport_bill_line(models.Model):
    _name = 'transport.bill.line'

    def get_purchase_cost(self):
        self.ensure_one()
        purchase_cost = 0
        for i in self.lot_plan_ids.filtered(lambda x: x.stage_1):
            purchase_cost += i.lot_id.pol_id.currency_id.compute(i.qty * i.lot_id.purchase_price, self.company_currency_id)
        return purchase_cost

    def get_stock_cost(self):
        self.ensure_one()
        stock_cost = 0
        for i in self.lot_plan_ids.filtered(lambda x: x.stage_2 and not x.stage_1):
            stock_cost += i.lot_id.pol_id.currency_id.compute(i.qty * i.lot_id.purchase_price, self.company_currency_id)
        return stock_cost

    @api.depends('sol_id','sol_id.order_id','sol_id.order_id.name','sol_id.product_id','sol_id.product_id.name')
    def compute_name(self):
        for one in self:
            if one.sol_id:
                one.name = '%s:%s' % (one.sol_id.order_id.name, one.sol_id.product_id.name)



    def compute_info(self):
        for one in self:
            sol = one.sol_id
            if not sol: continue
            plan_lots = one.lot_plan_ids
            one.qty1stage = sum([x.qty for x in plan_lots.filtered(lambda x: x.stage_1 == True)])
            qty2stage = sum([x.qty for x in plan_lots.filtered(lambda x: x.stage_2 == True)])
            # one.qty2stage = sum([x.qty for x in plan_lots.filtered(lambda x: x.stage_2 == True)])
            ##计算金额
            discount = one.discount
            cip_type = one.cip_type
            org_currency_sale_amount_origin = sol.price_unit * qty2stage
            org_currency_sale_amount = sol.price_unit * qty2stage * (1- (discount or 0.0)/100 )
            org_currency_sale_amount_discount = org_currency_sale_amount_origin * ((discount or 0.0)/100)


            sale_amount = one.sale_currency_id.compute(org_currency_sale_amount, one.company_currency_id)
            purchase_cost = one.get_purchase_cost()
            stock_cost = one.get_stock_cost()
            back_tax = cip_type != 'none' and one.back_tax or 0
            back_tax_amount = (purchase_cost + stock_cost) / BACK_TAX_RATIO * back_tax
            vat_diff_amount = 0
            if one.include_tax  and one.company_currency_id.name == 'CNY':
                vat_diff_amount = (sale_amount - purchase_cost -stock_cost)/ 1.13 * 0.13
            profit_amount = sale_amount - purchase_cost - stock_cost + back_tax_amount - vat_diff_amount
            one.org_currency_sale_amount = org_currency_sale_amount
            one.sale_amount = sale_amount
            one.purchase_cost = purchase_cost
            one.stock_cost = stock_cost
            one.back_tax_amount = back_tax_amount
            one.vat_diff_amount = vat_diff_amount
            one.profit_amount = profit_amount
            one.org_currency_sale_amount_origin = org_currency_sale_amount_origin
            one.org_currency_sale_amount_discount = org_currency_sale_amount_discount

    @api.depends('lot_plan_ids','lot_plan_ids.qty','lot_plan_ids.lot_id.purchase_price','lot_plan_ids.stage_1','lot_plan_ids.lot_id.pol_id.currency_id')
    def compute_purchase_cost_new(self):
        for one in self:
            purchase_cost_new = one.get_purchase_cost()
            one.purchase_cost_new = purchase_cost_new

    @api.depends('sol_id.new_rest_tb_qty','sol_id')
    def compute_rest_tb_qty(self):
        for one in self:
            one.rest_tb_qty = one.sol_id.new_rest_tb_qty

    # 13ok
    @api.depends('lot_plan_ids', 'lot_plan_ids.stage_2', 'lot_plan_ids.qty', 'plan_qty')
    def compute_qty2stage_new(self):
        for one in self:
            plan_lots = one.lot_plan_ids
            one.qty2stage_new = sum([x.qty for x in plan_lots.filtered(lambda x: x.stage_2 == True)])




   #akiny暂时不要
    stage3move_ids = fields.Many2many('stock.move', 'ref_move_tbl', 'lid', 'mid', u'出库',
                                      domain=[('picking_code', '=', 'outgoing')])


    vat_diff_amount = fields.Monetary(u'增值税差额', currency_field='company_currency_id', compute=compute_info,
                                      digits=dp.get_precision('Money'))
    profit_amount = fields.Monetary(u'利润', currency_field='company_currency_id', compute=compute_info,
                                    digits=dp.get_precision('Money'))

    s_uom_id = fields.Many2one('product.uom', u'销售打印单位', related='product_id.s_uom_id')
    p_uom_id = fields.Many2one('product.uom', u'采购打印单位', related='product_id.p_uom_id')

    #currency_id = fields.Many2one(related='bill_id.currency_id', readonly=True, string='公司本币') #TODO
    company_currency_id = fields.Many2one('res.currency', string='公司货币', related='bill_id.company_currency_id', readonly=True)
    sale_currency_id = fields.Many2one(related='bill_id.sale_currency_id', readonly=True)
    third_currency_id = fields.Many2one(related='bill_id.third_currency_id', readonly=True)

    #13添加

    discount = fields.Float(string='Discount (%)',digits=(16, 20), related='sol_id.discount', store=True,)
    back_tax_amount = fields.Monetary(u'退税金额', currency_field='company_currency_id', compute=compute_info,
                                      digits=dp.get_precision('Money'))
    org_currency_sale_amount = fields.Monetary(u'销售货币金额', currency_field='sale_currency_id', compute=compute_info,
                                               store=False, digits=dp.get_precision('Money'))
    org_currency_sale_amount_discount = fields.Monetary(u'折扣', currency_field='sale_currency_id',
                                                      compute=compute_info,
                                                      store=False, digits=dp.get_precision('Money'))
    org_currency_sale_amount_origin =  fields.Monetary(u'销售货币金额', currency_field='sale_currency_id', compute=compute_info,
                                               store=False, digits=dp.get_precision('Money'))
    sale_amount = fields.Monetary(u'销售金额', currency_field='company_currency_id', compute=compute_info, store=False,
                                  digits=dp.get_precision('Money'))
    purchase_cost = fields.Monetary(u'采购成本', currency_field='company_currency_id', compute=compute_info,
                                    digits=dp.get_precision('Money'))
#1102
    purchase_cost_new = fields.Monetary(u'采购成本', currency_field='company_currency_id', compute=compute_purchase_cost_new, store=True,
                                    digits=dp.get_precision('Money'))
    stock_cost = fields.Monetary(u'库存成本', currency_field='company_currency_id', compute=compute_info,
                                 digits=dp.get_precision('Money'))
    name = fields.Char(u'说明', compute=compute_name,store=True)
    bill_id = fields.Many2one('transport.bill', u'发运单', ondelete='cascade', required=True)
    include_tax = fields.Boolean(related='bill_id.include_tax')
    state = fields.Selection(related='bill_id.state')
    sol_id = fields.Many2one('sale.order.line', u'销售明细',)
    po_id = fields.Many2one('purchase.order',related='sol_id.po_id')
    # rest_tb_qty = fields.Float(related='sol_id.rest_tb_qty')
    rest_tb_qty = fields.Float(compute=compute_rest_tb_qty)
    cip_type = fields.Selection(related='bill_id.cip_type', readonly=True)
    smline_ids = fields.One2many('stock.move.line', related='sol_id.smline_ids', string=u'库存预留')
    smline_str = fields.Char(related='sol_id.smline_str', string=u'锁定内容')
    smline_qty = fields.Float(related='sol_id.smline_qty', string=u'锁定总数')
    dlr_ids = fields.One2many('dummy.lot.reserve', related='sol_id.dlr_ids', string=u'采购预留')
    dlr_str = fields.Char(related='sol_id.dlr_str', string=u'采购预留')
    dlr_qty = fields.Float(related='sol_id.dlr_qty', string=u'采购预留数')
    lot_plan_ids = fields.One2many('transport.lot.plan', 'tbline_id', u'调拨计划', copy=False)
    lot_plan_id = fields.Many2one('transport.lot.plan',  u'调拨计划:新')
    #1102
    customer_id = fields.Many2one('res.partner',u'客户',related='bill_id.partner_id',store=True)
    supplier_id = fields.Many2one('res.partner','供应商',related='lot_plan_id.lot_id.supplier_id')
    plan_lot = fields.Many2one('stock.production.lot',  '计划批次', related='lot_plan_id.lot_id')
    plan_qty = fields.Float('计划数量', related='lot_plan_id.qty')
    pol_ids = fields.One2many('purchase.order.line', related='sol_id.pol_ids', readonly=True)
    move_ids = fields.Many2many('stock.move', 'ref_move_tbl', 'lid', 'mid', u'库存移动详情')
    stage1move_ids = fields.Many2many('stock.move', 'ref_move_tbl', 'lid', 'mid', u'入库',
                                      domain=[('picking_code', '=', 'incoming')])
    stage2move_ids = fields.Many2many('stock.move', 'ref_move_tbl', 'lid', 'mid', u'出库',
                                      domain=[('picking_code', '=', 'outgoing')])
    purchase_qty = fields.Float(u'采购数', related='sol_id.purchase_qty')
    qty_unreceived = fields.Float(u'未收数', related='sol_id.qty_unreceived')
    so_id = fields.Many2one('sale.order', u'销售单', related='sol_id.order_id', readonly=True)
    sale_contract_code = fields.Char(u'合同编码', related='so_id.contract_code', readonly=True)
    product_id = fields.Many2one('product.product', related='sol_id.product_id', string=u'产品', readonly=True)
    hs_id = fields.Many2one('hs.hs', u'品名', related='product_id.hs_id', readonly=True)
    back_tax = fields.Float(u'退税率', digits=dp.get_precision('Back Tax'))
    sale_qty = fields.Float(u'销售数', related='sol_id.product_uom_qty', readonly=True)
    qty_delivered = fields.Float(u'已发货', related='sol_id.qty_delivered', readonly=True)
    qty_undelivered = fields.Float(u'未发货', related='sol_id.qty_undelivered', readonly=True)
    qty = fields.Float(u'发运数量')
    qty1stage = fields.Float(u'入库数', compute=compute_info)
    # qty2stage = fields.Float(u'发货数', compute=compute_info)
    qty2stage_new = fields.Float(u'发货数:新', compute='compute_qty2stage_new', store=True)
    pack_line_id = fields.Many2one('transport.pack.line', u'统计')
    #明细装箱统计
    qty_package = fields.Float('数量/大包装')
    package_qty = fields.Float('大包装数量')
    gross_weight = fields.Float('毛重', digits=dp.get_precision('Weight'))
    net_weight = fields.Float('净重', digits=dp.get_precision('Weight'))
    volume = fields.Float('体积', digits=dp.get_precision('Volume'))
    #批次明细
    tbl_lot_ids = fields.One2many('bill.line.lot', 'tb_line_id', string='明细批次')
    so_tb_number = fields.Char('销售合同发货次数')
    is_gold_sample = fields.Boolean('是否有金样', related='product_id.is_gold_sample', readonly=False)
    is_ps = fields.Boolean('是否有PS', related='product_id.is_ps', readonly=False)
#----

    need_print = fields.Boolean('是否打印', default=True)
    #是否金样  akiny

    #单个费用 akiny
    # fee_inner = fields.Monetary(u'国内运杂费:单个', currency_field='company_currency_id', compute=compute_info)
    # fee_rmb1 = fields.Monetary(u'人民币费用1:单个', currency_field='company_currency_id', compute=compute_info)
    # fee_rmb2 = fields.Monetary(u'人民币费用2:单个', currency_field='company_currency_id', compute=compute_info)
    # fee_outer = fields.Monetary(u'国外运保费', currency_field='other_currency_id', compute=compute_info)
    # fee_export_insurance = fields.Monetary(u'出口保险费:单个', currency_field='other_currency_id', compute=compute_info)
    # fee_other = fields.Monetary(u'其他外币费用:单个', currency_field='other_currency_id', compute=compute_info)
    #
    # outer_currency_id = fields.Many2one('res.currency', u'国外运保费货币', related='order_id.outer_currency_id')
    # export_insurance_currency_id = fields.Many2one('res.currency', u'出口保险费货币',
    #                                                related='order_id.export_insurance_currency_id')
    # other_currency_id = fields.Many2one('res.currency', u'其他国外费用货币', related='order_id.other_currency_id')
    #这次出运单的批次







#13ok
    @api.onchange('sol_id')
    def onchange_sol(self):
        self.back_tax = self.sol_id.product_id.back_tax
        self.need_print = self.sol_id.product_id.back_tax.need_print

  #13取消
    def compute_tbl_lot(self):
        obj = self.env['bill.line.lot']
        records = obj.browse([])
        for one in self:
            for i in one.smline_ids.filtered(lambda x: x.product_uom_qty > 0):
                records |= obj.create({
                    'tb_line_id': one.id,
                    'tb_id': one.bill_id.id,
                    'lot_id': i.lot_id.id,
                    'qty': i.product_uom_qty,
                })
            for j in one.dlr_ids.filtered(lambda x: x.qty > 0):
                records |= obj.create({
                    'tb_line_id': one.id,
                    'tb_id': one.bill_id.id,
                    'lot_id': j.lot_id.id,
                    'qty': j.qty,
                })
            one.tbl_lot_ids = records

   #13ok
    @api.multi
    def make_default_lot_plan(self):
        plan_obj = self.env['transport.lot.plan']
        for line in self:
            #line.plan_lot = line.sol_id.lot_id
            #line.plan_qty = line.sol_id.rest_tb_qty

            line.lot_plan_ids = False
            for x in line.dlr_ids.filtered(lambda x: x.todo_qty > 0):
                plan =plan_obj.create({
                    'tbline_id': line.id,
                    'lot_id': x.lot_id.id,
                    #'qty': x.todo_qty,
                    'qty': line.sol_id.rest_tb_qty,
                    'stage_1': True,
                    'stage_2': True,
                })
                line.lot_plan_id = plan

            for x in line.smline_ids.filtered(lambda x: x.state != 'done'):
                plan_obj.create({
                    'tbline_id': line.id,
                    'lot_id': x.lot_id.id,
                    #'qty': x.product_uom_qty,
                    'qty': line.sol_id.rest_tb_qty,
                    'stage_1': False,
                    'stage_2': True,
                })
 #13ok
    def get_dict_plan_lots(self, stage):
        self.ensure_one()
        plan_lots = self.lot_plan_ids
        if stage == 1:
            plan_lots = plan_lots.filtered(lambda x: x.stage_1 == True)
        elif stage == 2:
            plan_lots = plan_lots.filtered(lambda x: x.stage_2 == True)
        elif stage == 3:
            plan_lots = plan_lots.filtered(lambda x: x.stage_3 == True)
        else:
            raise Warning(u'stage %s 参数错误' % stage)

        res = dict([(x.lot_id, 0) for x in plan_lots])
        for i in plan_lots:
            res[i.lot_id] += i.qty
        return res
#ok
    def _prepare_1_picking(self):
        todo_moves = self.env['stock.move']
        for line in self:
            # 写入move_line 完成数量
            lot_dic = line.get_dict_plan_lots(1)
            sol = line.sol_id
            moves = sol.dlr_ids.mapped('pol_id').mapped('move_ids').filtered(
                lambda x: x.state not in ['cancel', 'done'])

            for m in moves:
                for ml in m.move_line_ids:
                    lot = ml.lot_id
                    if lot_dic.get(lot):
                        ml.qty_done = lot_dic[lot]
                        line.move_ids |= m

    # 13ok
    def _new_prepare_2_picking(self):
        pass

    # 13ok
    def _prepare_2_picking(self):
        #todo_moves = self.env['stock.move']
        ##pick_type = self.env.ref('stock.picking_type_out')

        pick_type = self.env['stock.picking.type'].search([('ref', '=', 'delivery'),('company_id', '=', self.env.user.company_id.id)], limit=1)

        wizard_msrl = self.env['wizard.manual.stock.reserve.line']
        wizard_item_obj = self.env['wizard.manual.stock.reserve.item']
        for line in self:
            lot_dic = line.get_dict_plan_lots(2)
            #print('====lot_dic==', lot_dic)
            sol = line.sol_id
            moves = sol.order_id.picking_ids.mapped('move_lines').filtered(
                lambda m: m.picking_type_id == pick_type
                          and m.product_id == line.product_id
                          and m.state not in ['cancel', 'done', 'draft'])

            print('====moves==', moves, pick_type)
            for move in moves:
                wizard = wizard_msrl.create({'move_id': move.id})
                for lot in lot_dic:
                    wizard_item_obj.create({
                        'line_id': wizard.id,
                        'new_lot_id': lot.id,
                        'new_qty': lot_dic[lot],

                    })
                wizard.apply()
                line.move_ids |= move

            # print('===', moves, sol.order_id.picking_ids)
            # for m in moves:
            #     if m.move_line_ids:
            #         for ml in m.move_line_ids:
            #             lot = ml.lot_id
            #             if lot_dic.get(lot):
            #                 ml.qty_done = lot_dic[lot]
            #                 line.move_ids |= m
            #     else:
            #         pass

    @api.onchange('qty')
    def onchange_qty(self):
        self.qty1stage = self.qty
    #13 ok
    def open_wizard_transport_lot_plan(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        wzline_obj = self.env['wizard.transport.lot.plan.line']
        wizard = self.env['wizard.transport.lot.plan'].create({'tbline_id': self.id, })
        for plan in self.lot_plan_ids:
            wzl = wzline_obj.create({
                'wizard_id': wizard.id,
                'plan_id': plan.id,
                # 'qty': plan.qty,
                # 'stage_1': plan.stage_1,
                # 'stage_2': plan.stage_2,
                # 'lot_id': plan.lot_id.id,
            })
            wzl.onchage_plan()

        view = self.env.ref('yjzy_extend.wizard_transport_lot_plan_form')
        return {
            'name': u'计划',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view.id,
            'res_model': 'wizard.transport.lot.plan',
            'res_id': wizard.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
            # 'context': ctx,
        }

