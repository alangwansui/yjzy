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
        if not self.tb_po_line_ids:
            tb_po_line_obj = self.env['tb.po.line']
            po_ids = self.line_ids.mapped('po_id')
            for po in po_ids:
                po_tb_amount = sum(x.purchase_cost_new for x in self.line_ids.filtered(lambda x: x.po_id == po))
                pre_advance_line = po.pre_advance_line.filtered(lambda x: x.pre_advance_options == 'before_delivered')
                tb_po_line = tb_po_line_obj.create({
                    'tb_id': self.id,
                    'po_id': po.id,
                    'po_tb_amount': po_tb_amount,
                    'pre_advance_id': pre_advance_line.id
                })
                tb_po_line.compute_po_tb_percent()
                tb_po_line.compute_pre_advance_total()
        self.update_po_supplier_amount()

    def update_po_supplier_amount(self):
        tb_po_line_ids = self.tb_po_line_ids
        supplier_ids = self.line_ids.mapped('supplier_id')
        print('supplier_ids_akiny',supplier_ids)
        for one in supplier_ids:
            for line in tb_po_line_ids:
                if line.tb_po_supplier == one:
                    line.po_supplier_amount = sum(x.po_tb_amount for x in self.tb_po_line_ids.filtered(lambda x: x.tb_po_supplier == one))


class transport_purchase_order(models.Model):
    _name = 'tb.po.line'
    _description = u'出运采购合并'

    @api.depends('po_tb_amount','po_amount')
    def compute_po_tb_percent(self):
        for one in self:
            tb_po_amount = one.tb_po_amount
            po_tb_amount = one.po_tb_amount
            po_amount = one.po_amount
            po_tb_percent = tb_po_amount != 0.0 and po_tb_amount / tb_po_amount or 0.0  # 本次出运占整个采购的总金额
            po_po_tb_percent = po_amount != 0.0 and po_tb_amount / po_amount or 0.0
            one.po_tb_percent = po_tb_percent
            one.po_po_tb_percent = po_po_tb_percent


    #注意合并后，采购合同不一样的同时，供应商也会不一样，所以预付的时候还要考虑供应商
    tb_id = fields.Many2one('transport.bill', u'出运单',ondelete='cascade')
    po_id = fields.Many2one('purchase.order',u'采购合同')
    pre_payment_id = fields.Many2one('account.payment','预付款单')

    po_currency_id = fields.Many2one('res.currency','采购货币',default=lambda self: self.env.user.company_id.currency_id)
    po_tb_amount = fields.Monetary('出运采购金额',currency_field='po_currency_id')
    po_tb_percent = fields.Float('出运采购金额占出运总金额',compute=compute_po_tb_percent,store=True)
    po_po_tb_percent = fields.Float('出运采购金额占原始采购金额',compute=compute_po_tb_percent,store=True)
    #按照供应商分组后，分别计算，每个出运采购占总的相同供应商的出运金额比例,做预付申请的时候需要的比例
    @api.depends('po_supplier_amount','po_tb_amount')
    def compute_po_supplier_percent(self):
        for one in self:
            one.po_supplier_percent = one.po_supplier_amount != 0  and one.po_tb_amount / one.po_supplier_amount or 0.0

    po_supplier_amount = fields.Monetary('相同供应商的采购出运金额',currency_field='po_currency_id')
    po_supplier_percent = fields.Float('相同供应商不同出运采购的比例',compute=compute_po_supplier_percent,store=True)
    tb_po_amount = fields.Monetary('出运采购总金额',currency_field='po_currency_id',related='tb_id.org_real_purchase_amount_new',store=True)
    po_amount = fields.Monetary('采购单采购金额',currency_field='po_currency_id',related='po_id.amount_total',store=True)
    tb_po_supplier = fields.Many2one('res.partner',related='po_id.partner_id',store=True)
    is_approved_prepayment = fields.Boolean('是否已经预付申请')

    #采集到采购单的发货前比例，之后*本次发货采购金额
    @api.depends('pre_advance_id','pre_advance_id.value_amount','po_tb_amount')
    def compute_pre_advance_total(self):
        for one in self:
            pre_advance_id = one.pre_advance_id
            pre_advance = pre_advance_id.value_amount
            po_tb_amount = one.po_tb_amount
            if pre_advance:
                pre_advance_total = (pre_advance / 100.0) * po_tb_amount
            else:
                pre_advance_total = 0
            one.pre_advance_total = pre_advance_total

    pre_advance_total = fields.Monetary('预计发货前支付金额',currency_field='po_currency_id',compute=compute_pre_advance_total,store=True)
    @api.depends('tbrl_ids','tbrl_ids.real_advance_amount')
    def _compute_real_advance_amount(self):
        for one in self:
            one.real_advance_amount = sum(x.real_advance_amount for x in one.tbrl_ids)

    @api.depends('pre_payment_id', 'pre_payment_id.amount')
    def compute_real_advance_amount(self):
        for one in self:
            one.real_advance_amount = one.pre_payment_id.amount

    pre_advance_id = fields.Many2one('pre.advance', 'Advice Advance Line',ondelete='restrict')
    tbrl_ids = fields.One2many('tb.po.real.line','tpl_id','实际预付合计')
    real_advance_amount = fields.Monetary('实际预付金额',currency_field='po_currency_id',compute=compute_real_advance_amount)


    state = fields.Selection([('draft','Draft'),
                              ('creating',u'创建中'),
                              ('approval','审批中'),
                              ('done','Done')
                              ],'state',default='draft')


class transport_purchase_real_payment(models.Model):
    _name = 'tb.po.real.line'
    _description = u'实际出运前预付'


    tpl_id = fields.Many2one('tb.po.line','合并的出运采购',ondelete='cascade')
    po_currency_id = fields.Many2one('res.currency', '采购货币', default=lambda self: self.env.user.company_id.currency_id)
    real_advance_amount = fields.Monetary('实际预付金额', currency_field='po_currency_id')
    state = fields.Selection([('draft','Draft'),('approval','Approval'),('done','Done')],'state',default='draft')





