# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning


class wizard_po_box(models.TransientModel):
    _name = 'wizard.po.box'
    _description = '分配箱号'

    box_type = fields.Selection([('b', 'B'), ('a', 'A')], string=u'编号方式', default='a')
    box_start = fields.Integer(u'开始箱号', default=1)

    def apply(self):
        self.ensure_one()
        ctx = self.env.context
        po = self.env['purchase.order'].browse(ctx.get('active_id'))
        if self.box_type == 'a':
            for line in po.order_line:
                if line.product_id.type != 'product':
                    continue

                if line.box_start:
                    raise Warning(u'已经存在箱号,请勿重复编号')
                box_qty = line.product_id.get_package_info(line.product_qty)['max_qty']
                line.box_start = 1
                line.box_end = box_qty

        if self.box_type == 'b':
            start = end = self.box_start
            for line in po.order_line:
                if line.box_start:
                    raise Warning(u'已经存在箱号,请勿重复编号')
                box_qty = line.product_id.get_package_info(line.product_qty)['max_qty']

                end += box_qty - 1
                line.box_start = start
                line.box_end = end
                start += box_qty - 1

                start += 1
                end += 1

        return True




