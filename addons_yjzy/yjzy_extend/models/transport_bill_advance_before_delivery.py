# -*- coding: utf-8 -*-
from num2words import num2words
from odoo import models, fields, api, _
from odoo.exceptions import Warning
from . comm import BACK_TAX_RATIO

class transport_bill(models.Model):
    _inherit = 'transport.bill'

    tb_po_line_ids = fields.One2many('tb.po.line','tb_id','出运采购合并')
    #创建出运采购合并，兵器而计算各个采购的出运金额，并且最终体现在pre.adnvance的统计上。
    def create_tb_po_line_ids(self):
        tb_po_line_obj = self.env['tb.po.line']
        po_ids = self.line_ids.mapped('po_id')
        for po in po_ids:
            po_tb_amount = sum(x.purchase_cost_new for x in self.line_ids.filtered(lambda x: x.po_id == po))
            pre_advance_line = po.pre_advance_line.filtered(lambda x: x.pre_advance_options == 'before_delivered')
            tb_po_line = tb_po_line_obj.create({
                'tb_id':self.id,
                'po_id':po.id,
                'po_tb_amount':po_tb_amount,
                'pre_advance_id':pre_advance_line.id
            })
            tb_po_line.compute_po_tb_percent()
            tb_po_line.compute_pre_advance_total()


class transport_purchase_order(models.Model):
    _name = 'tb.po.line'
    _description = u'出运采购合并'

    @api.depends('tb_po_amount','po_tb_amount')
    def compute_po_tb_percent(self):
        for one in self:
            tb_po_amount = one.tb_po_amount
            po_tb_amount = one.po_tb_amount
            po_tb_percent = tb_po_amount != 0.0 and po_tb_amount / tb_po_amount or 0.0
            one.po_tb_percent = po_tb_percent



    tb_id = fields.Many2one('transport.bill', u'出运单',ondelete='cascade')
    po_id = fields.Many2one('purchase.order',u'采购合同')
    po_currency_id = fields.Many2one('res.currency','采购货币',default=lambda self: self.env.user.company_id.currency_id)
    po_tb_amount = fields.Monetary('采购金额',currency_field='po_currency_id')
    po_tb_percent = fields.Float('采购金额占出运合同总采购金额比例',compute=compute_po_tb_percent,store=True)
    tb_po_amount = fields.Monetary('出运采购总金额',currency_field='po_currency_id',related='tb_id.org_real_purchase_amount_new',store=True)
    #采集到采购单的发货前比例，之后进行计算
    @api.depends('pre_advance_id','pre_advance_id.value_amount','po_tb_percent','po_id.amount_total','po_id')
    def compute_pre_advance_total(self):
        for one in self:
            pre_advance_id = one.pre_advance_id
            pre_advance = pre_advance_id.value_amount
            po_tb_percent = one.po_tb_percent
            po_tb_amount = one.po_tb_amount
            if pre_advance:
                pre_advance_total = (pre_advance / 100.0) * po_tb_amount
            else:
                pre_advance_total = 0
            one.pre_advance_total = pre_advance_total


    pre_advance_total = fields.Monetary('预计发货前支付金额',currency_field='po_currency_id',compute=compute_pre_advance_total,store=True)

    pre_advance_id = fields.Many2one('pre.advance', 'Advice Advance Line')
    real_advance_amount = fields.Monetary('实际预付金额',currency_field='po_currency_id')


    state = fields.Selection([('draft','Draft'),
                              ('posted','Posted')
                              ],'state',defautl='draft')






