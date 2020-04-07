# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning


class account_invoice(models.Model):
    _inherit = 'account.invoice'

    @api.depends('payment_term_id', 'date_due')
    def compute_date_deadline(self):
        strptime = datetime.strptime
        for one in self:
            if one.date_due and one.date_invoice and one.payment_term_id.invoice_date_deadline_field:
                dump_date = getattr(one, one.payment_term_id.invoice_date_deadline_field)
                if not dump_date:
                    continue
                diff = strptime(dump_date, DF) - strptime(one.date_invoice, DF)
                one.date_deadline = (strptime(one.date_due, DF) + diff).strftime(DF)

    yjzy_type = fields.Selection([('sale', u'销售'), ('purchase', u'采购'), ('back_tax', u'退税')], string=u'发票类型')
    bill_id = fields.Many2one('transport.bill', u'发运单')
    tb_contract_code = fields.Char(u'出运合同号', related='bill_id.ref', readonly=True)
    include_tax = fields.Boolean(u'含税', related='bill_id.include_tax')

    date_ship = fields.Date(u'出运船日期')
    date_finish = fields.Date(u'交单日期')
    reconcile_order_id = fields.Many2one('account.reconcile.order', u'核销单据')

    move_ids = fields.One2many('account.move', 'invoice_id', u'发票相关的分录', help=u'记录发票相关的分录，方便统计')
    move_line_ids = fields.One2many('account.move.line', 'invoice_id', u'发票相关的分录明细', help=u'记录发票相关的分录明细，方便统计')
    date_deadline = fields.Date(u'到期日期', compute=compute_date_deadline)

    item_ids = fields.One2many('invoice.hs_name.item', 'invoice_id', u'品名汇总明细')
    po_id = fields.Many2one('purchase.order', u'采购订单')
    purchase_contract_code = fields.Char(u'合同编码', related='po_id.contract_code', readonly=True)

    sale_assistant_id = fields.Many2one('res.users', u'业务助理')
    gongsi_id = fields.Many2one('gongsi', '内部公司')


    def name_get(self):
        ctx = self.env.context
        print('=111====', ctx)
        res = []
        for one in self:
            if ctx.get('params', {}).get('model', '') == 'transport.bill':
                name = '%s:%s' % (one.number, one.date_finish)
            else:
                name = one.number
            res.append((one.id, name))
        return res

    def clear_zero_line(self):
        for one in self:
            for line in one.invoice_line_ids:
                if line.quantiy == 0:
                    line.unlink()


    def make_hs_name_items(self):
        self.ensure_one()
        self.item_ids.unlink()

        item_obj = self.env['invoice.hs_name.item']
        dic_hs_lines = {}
        for line in self.invoice_line_ids:
            hs_name = line.product_id.hs_name
            if hs_name not in dic_hs_lines:
                dic_hs_lines[hs_name] = line
            else:
                dic_hs_lines[hs_name] |= line

        for hs_name, lines in dic_hs_lines.items():
            item = item_obj.create({
                'invoice_id': self.id,
                'name': hs_name,
            })
            item.invoice_line_ids = lines
            item.compute_info()


class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    @api.depends('sale_line_ids')
    def _compute_so(self):
        for one in self:
            one.so_id = one.sale_line_ids and one.sale_line_ids[0].order_id or False

    item_id = fields.Many2one('invoice.hs_name.item', 'Item')

    so_id = fields.Many2one('sale.order', u'销售订单', compute=_compute_so)


class invoice_hs_name_item(models.Model):
    _name = 'invoice.hs_name.item'

    def compute_info(self):
        for one in self:
            one.product_id = one.invoice_line_ids.sorted(key=lambda x: x.quantity, reverse=True)[0].product_id
            one.qty = sum(one.invoice_line_ids.mapped('quantity'))
            one.amount = sum(one.invoice_line_ids.mapped('price_total'))
            one.price = one.amount / one.qty

    name = fields.Char('名称')
    invoice_id = fields.Many2one('account.invoice', u'发票')
    product_id = fields.Many2one('product.product', u'产品')
    qty = fields.Float(u'数量')
    price = fields.Float(u'价格')
    amount = fields.Float(u'金额', digits=dp.get_precision('Money'))
    invoice_line_ids = fields.One2many('account.invoice.line', 'item_id', 'Lines')
