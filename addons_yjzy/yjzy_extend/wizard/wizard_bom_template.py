# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning


class wizard_bom_template(models.TransientModel):
    _name = 'wizard.bom.template'
    _description = u'BOM复制向导'

    name = fields.Char(u'Name')
    product_template = fields.Many2one('product.template', u'产品')
    line_ids = fields.One2many('wizard.bom.template.line', 'wizard_id', u'明细')
    product_id = fields.Many2one('product.product', u'产品规格')

    @api.model
    def create(self, valus):
        wizard = super(wizard_bom_template, self).create(valus)
        bom_template = self.env.context.get('bom_template')
        if bom_template:
            wizard_line_obj = self.env['wizard.bom.template.line']
            for line in bom_template.line_ids:
                wizard_line_obj.create({
                    'wizard_id': wizard.id,
                    'product_tmpl_id': line.product_tmpl_id.id,
                    'product_id': line.product_id.id,
                    'qty': line.qty,
                })
        return wizard

    def check(self):
        self.ensure_one()
        for line in self.line_ids:
            if not line.product_id:
                raise Warning(u'明细产品不能为空')
            if line.qty <= 0:
                raise Warning(u'数量不能小于等于0')


    def apply(self):
        self.check()
        bom_line_obj = self.env['mrp.bom.line']
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_id.product_tmpl_id.id,
            'product_id': self.product_id.id,
            'product_qty': 1,
            'product_uom_id': self.product_id.uom_id.id,
        })
        for line in self.line_ids:
            bom_line_obj.create({
                'bom_id': bom.id,
                'product_id': line.product_id.id,
                'product_qty': line.qty,
                'product_uom_id': line.product_id.uom_id.id,
            })
        return True



class wizard_bom_template_line(models.TransientModel):
    _name = 'wizard.bom.template.line'

    wizard_id = fields.Many2one('wizard.bom.template', 'Wizard')
    product_tmpl_id = fields.Many2one('product.template', u'产品')
    product_id = fields.Many2one('product.product', u'产品规格', domain="[('product_tmpl_id', '=', product_tmpl_id)]")
    qty = fields.Float(u'数量')
