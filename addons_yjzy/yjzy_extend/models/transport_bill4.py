# -*- coding: utf-8 -*-
from num2words import num2words
from odoo import models, fields, api, _
from odoo.exceptions import Warning
from . comm import BACK_TAX_RATIO

class transport_bill(models.Model):
    _inherit = 'transport.bill'

    cgtj_line_ids = fields.One2many('cgtj.line', 'tb_id',  u'新采购统计')
    xstj_line_ids = fields.One2many('xstj.line', 'tb_id', u'新销售统计')


    def ___make_purchase_collect(self):

        self.cgtj_line_ids.unlink()


        res = {}   #key = hs.code + lot_name(poname)  {k: {'plan_ids':, 'po_id': }}
        cgtj_obj = self.env['cgtj.line']
        for plan in self.line_ids.mapped('lot_plan_ids'):
            hs = plan.lot_id.product_id.hs_id
            k = hs.code + ':' + plan.lot_id.name
            if not (k in res):
                res[k] = {'plan_ids': plan, 'po_id': plan.lot_id.po_id, 'hs_id': hs}
            else:
                res[k]['plan_ids'] |= plan

        for k in res:
            plans = res[k]['plan_ids']
            cgtj = cgtj_obj.create({
                'name': k,
                'tb_id': self.id,
                'hs_id': res[k]['hs_id'].id,
                'po_id': res[k]['po_id'].id,
                'qty': sum([x.qty for x in plans]),
                'amount': sum([x.qty * x.lot_id.purchase_price for x in plans]),

            })
            cgtj.plan_ids = plans

    def ___make_sale_collect(self):
        self.xstj_line_ids.unlink()

        obj = self.env['xstj.line']
        res = {}  #{hs: {}}
        for line in self.cgtj_line_ids:
            if not (line.hs_id in res):
                res[line.hs_id] = {'qty': line.qty, 'amount': line.amount, 'xstj_ids': line}
            else:
                res[line.hs_id]['qty'] += line.qty
                res[line.hs_id]['amount'] += line.amount
                res[line.hs_id]['xstj_ids'] |= line

        for hs in res:
            one = obj.create({
                'tb_id': self.id,
                'hs_id': hs.id,
                'qty': res[hs]['qty'],
                'amount': res[hs]['amount'],
            })
            one.xstj_ids = res[hs]['xstj_ids']



class cgtj_line(models.Model):
    _name = 'cgtj.line'
    _description = u'新采购统计'

    tb_id = fields.Many2one('transport.bill', u'出运单')
    hs_id = fields.Many2one('hs.hs', u'HS')
    plan_ids = fields.Many2many('transport.lot.plan',  'ref_plan_qctl', 'cid', 'pid',  u'计划')
    po_id = fields.Many2one('purchase.order', u'采购单')
    qty = fields.Float('数量')
    amount = fields.Float('金额')

    xstj_ids = fields.Many2one('xstj.line', u'新销售统计')



class xstj_line(models.Model):
    _name = 'xstj.line'
    _description = u'新销售统计'


    tb_id = fields.Many2one('transport.bill', u'出运单')
    hs_id = fields.Many2one('hs.hs', u'HS')
    qty = fields.Float('数量')
    amount = fields.Float('金额')
    #cgtj_ids = fields.One2many('cgtj.line', 'xstj_id', u'新采购统计')





