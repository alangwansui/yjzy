# -*- coding: utf-8 -*-

from odoo import models, fields, api


class transport_mark(models.Model):
    _name = 'transport.mark'
    _description = '唛头'

    name = fields.Char(u'唛头', required=True)
    content = fields.Html(u'内容', required=False)
    sequence = fields.Integer(u'排序')


class mark_comb(models.Model):
    _name = 'mark.comb'
    _description = '唛头组'

    name = fields.Char(u'名称', required=True)
    line_ids = fields.Many2many('transport.mark', 'ref_mark_comb', 'bid', 'mid', string=u'唛头')
    customer_id = fields.Many2one('res.partner','客户', domain=[('customer', '=', True),('parent_id', '=', False)])


class exchange_type(models.Model):
    _name = 'exchange.type'
    name = fields.Char(u'交单方式', required=True)


class exchange_demand_item(models.Model):
    _name = 'exchange.demand.item'
    name = fields.Char(u'要求项', required=True)

class exchange_demand_line(models.Model):
    _name = 'exchange.demand.line'

    name = fields.Char(u'值')
    item_id = fields.Many2one('exchange.demand.item', u'项')
    demand_id = fields.Many2one('exchange.demand', u'交单要求')


class exchange_demand(models.Model):
    _name = 'exchange.demand'

    name = fields.Char(u'交单要求')
    partner_id = fields.Many2one('res.partner', u'客户', required=True)
    line_ids = fields.One2many('exchange.demand.line', 'demand_id', u'明细')




class stock_wharf(models.Model):
    _name = 'stock.wharf'

    name = fields.Char(u'码头', required=True)
    code = fields.Char(u'编码', required=True)
    country_id = fields.Many2one('res.country', u'国家', required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', u"名称不能重复"),
        ('name_code', 'unique(code)', u"编码不能重复"),
    ]