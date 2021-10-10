# -*- coding: utf-8 -*-
from num2words import num2words
from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning


class transport_bill(models.Model):
    _inherit = 'transport.bill'

    tb_declare_line_ids = fields.One2many('tb.declare.line','tb_id',u'报关明细')

    def create_tb_declare_line_ids(self):
        self.ensure_one()
        self.tb_declare_line_ids.unlink()
        tb_declare_line_obj = self.env['tb.declare.line']
        hs_dic = {}
        for i in self.hsname_ids:
            amount2 = i.amount2
            purchase_amount2 = i.purchase_amount2
            out_qty2 = i.out_qty2
            hs_id = i.hs_id
            back_tax = i.back_tax
            k = hs_id.id
            if k in hs_dic:
                hs_dic[k]['out_qty2'] += out_qty2
                hs_dic[k]['amount2'] += amount2
                hs_dic[k]['purchase_amount2'] += purchase_amount2
            else:
                hs_dic[k] = {'out_qty2': out_qty2,
                             'amount2': amount2,
                             'purchase_amount2': purchase_amount2,
                             'back_tax': back_tax,
                             'hs_id': hs_id.id,
                             'tbl_hsname_id':i.id,
                             }
        for kk, data in list(hs_dic.items()):
            line = tb_declare_line_obj.create({
                'tb_id': self.id,
                'hs_id': data['hs_id'],
                'out_qty2': data['out_qty2'],
                'amount2': data['amount2'],
                'back_tax': data['back_tax'],
                'tbl_hsname_id':data['tbl_hsname_id'],
                'price2': data['amount2'] / (data['out_qty2'] or 1),
            })
            # print('>>', line)


class tb_declare_line(models.Model):
    _name = 'tb.declare.line'
    _description = u'实际报关明细'#差不多和tbl.hsname.all算法yiyang

    tbl_hsname_id = fields.Many2one('tbl.hsname', 'HS统计')
    tb_id = fields.Many2one('transport.bill', u'出运单', ondelete='cascade')
    currency_id = fields.Many2one('res.currency',u'币制',related='tb_id.sale_currency_id')
    hs_id = fields.Many2one('hs.hs', u'品名')
    hs_en_name = fields.Char(related='hs_id.en_name')
    back_tax = fields.Float(u'退税率', digits=dp.get_precision('Back Tax'))

    hs_id2 = fields.Many2one('hs.hs', u'报关品名')
    out_qty2 = fields.Float('报关数量',digits=(2,0))
    price2 = fields.Float('报关价格',digits=(2,2) )
    amount2 = fields.Monetary('报关金额',currency_field='currency_id' )
    source_area = fields.Char(u'境内货源地',related='tbl_hsname_id.source_area',store=True)
    source_country_id = fields.Many2one('res.country', u'原产国(地区)',related='tbl_hsname_id.source_country_id',store=True)
    partner_country_id = fields.Many2one('res.country', '最终目的国(地区)',related='tb_id.partner_country_id',store=True)
    keyword = fields.Char(u'报关要素',related='tbl_hsname_id.keyword',store=True)