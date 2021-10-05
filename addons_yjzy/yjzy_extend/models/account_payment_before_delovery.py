# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.addons.account.models.account_payment import account_payment as Account_Payment
from .comm import sfk_type, invoice_attribute_all_in_one
from odoo.addons import decimal_precision as dp
from datetime import datetime, timedelta


class account_payment(models.Model):
    _inherit = 'account.payment'

    prepayment_type = fields.Selection([('normal', '正常预付'),
                                        ('before_delivery', '出运前预付'),
                                        ], 'Prepayment Type', defualt='normal')  # 预付的两个type
    tb_id = fields.Many2one('transport.bill', u'出运合同', )#domain=[('state', '=', 'approve')]akiny
    tb_po_line_ids = fields.Many2many('tb.po.line', 'tpl', 'tb', 'po', u'出运采购合并')
    po_real_advance_before_delivery_new = fields.Monetary(u'实际发货前金额', currency_field='po_id_currency_id',
                                                          related='po_id.real_advance_before_delivery_new')
    tb_po_line_new_ids = fields.One2many('tb.po.line','pre_payment_id','发货前预付')
    # 筛选出
    @api.onchange('tb_id')
    def onchange_tb_po_line(self):
        for one in self:
            tb_po_line_ids = one.tb_id.tb_po_line_ids.filtered(lambda x: x.tb_po_supplier == one.partner_id)
            one.tb_po_line_ids = tb_po_line_ids
            tb_po_line_draft_ids = tb_po_line_ids.filtered(lambda x: x.state in ['draft','creating'])
            if one.tb_id:
                if len(tb_po_line_draft_ids) == 1:
                    one.tb_po_line_ids.state = 'creating'
                    one.po_id = tb_po_line_ids.po_id
                    one.pre_advance_id = tb_po_line_ids.pre_advance_id
                    one.is_pre_advance_line = True
                elif len(tb_po_line_draft_ids) > 1:
                    one.tb_po_line_ids[0].state = 'creating'
                    one.po_id = tb_po_line_ids[0].po_id
                    one.pre_advance_id = tb_po_line_ids[0].pre_advance_id
                    one.is_pre_advance_line = True
                else:
                    raise Warning('已经不存在需要发货前付款')
            else:
                one.po_id = False
                one.pre_advance_id = False
                one.is_pre_advance_line = False

            # po_ids = tb_po_line_ids.mapped('po_id')
            # if len(po_ids) == 1:
            #     po_id = po_ids
            #
            # else:
            #     po_id = po_ids[0]
            #
            # one.po_id = po_id
            # one.tb_po_line_ids = tb_po_line_ids.filtered(lambda x:x.po_id == po_id)

    def action_before_delivery_submit(self):
        self.tb_po_line_ids.is_approved_prepayment = True
        # obj = self.env['tb.po.real.line']
        # for x in self.tb_po_line_ids:
        #     tprl = obj.create({
        #         'tpl_id': x.id,
        #         'real_advance_amount': self.amount,
        #     })
        self.state_1 = '20_account_submit'
        for one in self.tb_po_line_ids:
            if one.state == 'creating':
                one.state = 'approval'
                one.pre_payment_id = self

        wizard_obj = self.env['wizard.prepayment.before.delivery']
        wizard_id = wizard_obj.with_context({'default_tb_po_line_ids': self.tb_po_line_ids.ids}).create({
            'tb_id': self.tb_id.id,
            'partner_id': self.partner_id.id
        })
        wizard_id.onchange_tb_po_line()
        form_view = self.env.ref('yjzy_extend.wizard_prepayment_before_delivery_form')
        return {
            'name': '创建预付申请',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.prepayment.before.delivery',
            'views': [(form_view.id, 'form')],
            'res_id': wizard_id.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
            # 'context': ctx,
        }

    def action_before_delivery_account_post(self):
        self.write({'state_1': '30_manager_approve'
                    })

    def action_before_delivery_manager_post(self):
        if self.po_id and self.po_id.so_id_state not in ['approve', 'sale']:
            raise Warning('合同未完成审批！')
        today = fields.date.today()
        self.write({'post_uid': self.env.user.id,
                    'post_date': today,
                    'state_1': '40_approve'
                    })
        self.create_rcfkd()

    def action_percent_amount(self):
        obj = self.env['tb.po.real.line']
        for x in self.tb_po_line_ids:
            tprl = obj.create({
                'tpl_id': x.id,
                'real_advance_amount': self.amount * x.po_supplier_percent,
            })

    # @api.onchange('tb_id')
    # def onchange_tb_id(self):
    #     for one in self.tb_po_line_ids:
    #         one.real_advance_amount = self.amount * one.po_tb_percent

    def action_manager_post(self):
        if self.po_id and self.po_id.so_id_state not in ['approve', 'sale']:
            raise Warning('合同未完成审批！')
        # elif self.tb_id.state not in ['approve']:
        #     raise Warning('出运合同未完成审批！')
        else:
            today = fields.date.today()
            self.write({'post_uid': self.env.user.id,
                        'post_date': today,
                        'state_1': '40_approve'
                        })
            self.create_rcfkd()
