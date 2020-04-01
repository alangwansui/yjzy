# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning


class wizard_transport_lot_plan(models.TransientModel):
    _name = 'wizard.transport.lot.plan'

    tbline_id = fields.Many2one('transport.bill.line', u'发运明细')
    product_id = fields.Many2one('product.product', related='tbline_id.product_id', string=u'产品')
    line_ids = fields.One2many('wizard.transport.lot.plan.line', 'wizard_id', u'明细', )

    def apply(self):
        self.ensure_one()
        plan_obj = self.env['transport.lot.plan']

        i = 1
        for line in self.line_ids:
            data = {'lot_id': line.lot_id.id, 'qty': line.qty, 'stage_1': line.stage_1, 'stage_2': line.stage_2}
            plan = line.plan_id

            if plan:
                plan.write(data)
            else:
                data.update({'tbline_id': self.tbline_id.id})
                plan = plan_obj.create(data)

            #明细的计划永远未第一条计划
            if i == 1:
                self.tbline_id.lot_plan_id = plan
            i += 1

        return True


class wizard_transport_lot_plan_line(models.TransientModel):
    _name = 'wizard.transport.lot.plan.line'

    wizard_id = fields.Many2one('wizard.transport.lot.plan', u'wizard')
    plan_id = fields.Many2one('transport.lot.plan')
    lot_id = fields.Many2one('stock.production.lot', u'批次')
    qty = fields.Float('数量')
    stage_1 = fields.Boolean('应用第1步', default=True)
    stage_2 = fields.Boolean('应用第2步', default=True)

    def unlink_plan(self):
        self.ensure_one()
        if self.plan_id:
            self.plan_id.unlink()
        self.unlink()

    @api.onchange('plan_id')
    def onchage_plan(self):
        plan = self.plan_id
        if plan:
            self.lot_id = plan.lot_id.id
            self.qty = plan.qty
            self.stage_1 = plan.stage_1
            self.stage_2 = plan.stage_2

#####################################################################################################################
