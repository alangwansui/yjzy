# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Sale_Order(models.Model):
    _inherit = 'sale.order'

    state2 = fields.Selection([('draft', u'草稿'), ('process', u'处理总'), ('delivery_done', u'发货完成'), ('signed', u'签字确认')],
                              u'订单状态', default='draft', copy=False)

    # @api.multi
    # def action_confirm(self):
    #     res = super(Sale_Order, self).action_confirm()
    #     self.write({'state2': 'process'})
    #     return res


    @api.multi
    def action_delivery_done(self):
        self.write({'state2': 'delivery_done'})



    @api.multi
    def action_signed(self):
        self.write({'state2': 'signed'})
        self.action_confirm()

