# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning


class wizard_prepayment_before_delivery(models.TransientModel):
    _name = 'wizard.prepayment.before.delivery'
    _description = '继续创建预付申请'

    tb_id = fields.Many2one('transport.bill', u'出运合同')
    tb_po_line_ids = fields.Many2many('tb.po.line', 'wtpl', 'tb', 'po', u'出运采购合并')
    partner_id = fields.Many2one('res.partner')
    po_id = fields.Many2one('purchase.order',u'采购合同')
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.user.company_id.currency_id)
    amount = fields.Monetary(string='金额',currency_field='currency_id',)


    @api.onchange('tb_id')
    def onchange_tb_po_line(self):
        for one in self:
            if one.tb_id:
                tb_po_line_ids = one.tb_po_line_ids.filtered(lambda x: x.state in ['draft'])
                if len(tb_po_line_ids) == 1:
                    one.tb_po_line_ids.state = 'creating'
                    one.po_id = tb_po_line_ids.po_id
                elif len(tb_po_line_ids) > 1:
                    one.tb_po_line_ids.state = 'creating'
                    one.po_id = tb_po_line_ids[0].po_id
                else:
                    one.cancel_1()
            else:
                one.po_id = False


    def cancel_1(self):
        self.ensure_one()
        # close popup
        return {'type': 'ir.actions.act_window_close'}

    def apply(self):
        yfsqd_obj = self.env['account.payment']
        domain = [('code', '=', 'yfdrl'), ('company_id', '=', self.env.user.company_id.id)]
        journal = self.env['account.journal'].search(domain, limit=1)
        account_code = '1123'
        advance_account = self.env['account.account'].search(
            [('code', '=', account_code), ('company_id', '=', self.env.user.company_id.id)], limit=1)
        yfsqd_id = yfsqd_obj.with_context({'display_name_code': 1, 'operation': 1, 'show_shoukuan': True, 'default_sfk_type': 'yfsqd',
         'default_payment_type': 'outbound', 'default_be_renling': True, 'default_advance_ok': True,
         'default_partner_type': 'supplier', 'default_tb_po_line_ids':self.tb_po_line_ids.ids}).create({
            'partner_id':self.partner_id.id,
            'tb_id':self.tb_id.id,
            'po_id':self.po_id.id,
            'journal_id':journal.id,
            'advance_account_id':advance_account.id,
            'payment_method_id':2,
            'amount':self.amount,
            'currency_id':self.currency_id.id,
        })
        form_view = self.env.ref('yjzy_extend.view_yfsqd_form')
        return {
            'name': u'预付申请单',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'views': [(form_view.id, 'form')],
            'res_id':yfsqd_id.id,
            'target': 'current',
            'context': {}
        }




