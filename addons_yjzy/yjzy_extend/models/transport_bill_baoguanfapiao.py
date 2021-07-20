# -*- coding: utf-8 -*-
from num2words import num2words
from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning


class transport_bill(models.Model):
    _inherit = 'transport.bill'

    plan_invoice_auto_ids = fields.One2many('plan.invoice.auto','bill_id','应收发票')
    real_invoice_auto_ids = fields.One2many('real.invoice.auto','bill_id','实际发票')

    def _action_lock_stage(self):
        stage_id = self._stage_find(domain=[('code', '=', '012')])
        self.write({'stage_id': stage_id.id})
        self.create_hsname_all_ids()
        self.create_btls_hs_ids_purchase()
        for one in self.plan_invoice_auto_ids:
            one.state_1 = '20'


    def action_lock_stage(self):
        self.locked = True
        print('locked_akiny',self.locked)
        if not self.tb_po_invoice_ids:
            self.create_hsname_all_ids()
            self.create_btls_hs_ids_purchase()
        stage_id = self._stage_find(domain=[('code', '=', '012')])
        self.write({'stage_id': stage_id.id})
        for one in self.plan_invoice_auto_ids:
            one.state_1 = '20'
            one.compute_state_1_2()


    def action_hexiao_stage(self):
        stage_id = self._stage_find(domain=[('code', '=', '007')])
        stage_preview = self.stage_id
        user = self.env.user
        if user not in stage_preview.user_ids:
            raise Warning('您没有权限审批')
        else:
            self.write({'stage_id': stage_id.id})
            # self.create_hsname_all_ids()
            # self.create_btls_hs_ids_purchase()

    def action_005_stage(self):
        stage_id = self._stage_find(domain=[('code', '=', '005')])
        stage_preview = self.stage_id
        user = self.env.user
        if user not in stage_preview.user_ids:
            raise Warning('您没有权限审批')
        else:
            self.write({'stage_id': stage_id.id})
            # self.create_hsname_all_ids()
            # self.create_btls_hs_ids_purchase()


    def action_finish_add_purchase_stage(self):
        stage_id = self._stage_find(domain=[('code', '=', '013')])
        stage_preview = self.stage_id
        user = self.env.user
        if user not in stage_preview.user_ids:
            raise Warning('您没有权限审批')
        else:
            self.write({'stage_id': stage_id.id})
            for one in self.plan_invoice_auto_ids:
                one.state = 'done'
