# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.addons.account.models.account_payment import account_payment as Account_Payment
from .comm import sfk_type, invoice_attribute_all_in_one
from odoo.addons import decimal_precision as dp
from datetime import datetime, timedelta



class account_payment(models.Model):
    _inherit = 'account.payment'

    prepayment_type = fields.Selection([('normal','Normal'),
                                        ('before_delivery','Before Delivery'),
                                        ],'Prepayment Type',defualt='normal')#预付的两个type


    tb_id = fields.Many2one('transport.bill',u'出运合同',domain=[('state','=','approve')])
    tb_po_line_ids = fields.Many2many('tb.po.line','tpl','tb','po',u'出运采购合并')

    @api.onchange('tb_id')
    def onchange_tb_po_line(self):
        for one in self:
            one.tb_po_line_ids = one.tb_id.tb_po_line_ids



    def action_percent_amount(self):
        for x in self.tb_po_line_ids:
            self.real_advance_amount = self.amount * x.po_tb_percent

    # @api.onchange('tb_id')
    # def onchange_tb_id(self):
    #     for one in self.tb_po_line_ids:
    #         one.real_advance_amount = self.amount * one.po_tb_percent

    def action_manager_post(self):
        if self.po_id and self.po_id.so_id_state not in ['approve', 'sale']:
            raise Warning('合同未完成审批！')
        elif self.tb_id.state not in ['approve']:
            raise Warning('出运合同未完成审批！')
        else:
            today = fields.date.today()
            self.write({'post_uid': self.env.user.id,
                        'post_date': today,
                        'state_1': '40_approve'
                        })
            self.create_rcfkd()