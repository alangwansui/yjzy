# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class Stock_Pikcing(models.Model):
    _inherit = 'stock.picking'

    date_ship = fields.Datetime(u'船期')
    date_finish = fields.Datetime(u'交单日期')


class stock_move(models.Model):
    _inherit = 'stock.move'
    s_uom_id = fields.Many2one('product.uom', u'销售打印单位', related='product_id.s_uom_id')
    p_uom_id = fields.Many2one('product.uom', u'采购打印单位', related='product_id.p_uom_id')



class Stock_Pikcing_Type(models.Model):
    _inherit = 'stock.picking.type'

    ref = fields.Char(u'编码')
    company_id = fields.Many2one('res.company', u'公司', related='warehouse_id.company_id', readonly=True)

    @api.constrains('ref', 'warehouse_id')
    def check_ref(self):
        if self.search_count([('ref','=',self.ref),('warehouse_id','=', self.warehouse_id.id)]) > 1:
            raise Warning(u'仓库的调拨类型不允许重复')









