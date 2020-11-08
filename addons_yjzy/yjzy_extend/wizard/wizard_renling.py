# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning


class wizard_renling(models.TransientModel):
    _name = 'wizard.renling'

    @api.depends('partner_id')
    def compute_invoice_advance(self):
        sale_other_invoice_ids = self.env['account.invoice'].search(
            [('residual', '>', 0), ('state', '=', 'open'), ('invoice_attribute', '=', 'other_payment'),
             ('yjzy_type_1', '=', 'sale'), ('type', '=', 'out_invoice')])
        self.sale_other_invoice_ids = sale_other_invoice_ids



    partner_id = fields.Many2one('res.partner', u'合作伙伴', domain=[('customer', '=', True)])
    yjzy_payment_id = fields.Many2one('account.payment',u'日常收款单')
    gongsi_id = fields.Many2one('gongsi', '内部公司')

    invoice_ids = fields.Many2many('account.invoice', 'ref_wz_inv', 'inv_id', 'wz_id', u'Invoice')
    so_id = fields.Many2one('sale.order','销售合同')
    btd_id = fields.Many2one('back.tax.declaration','退税申报单')
    sale_other_invoice_ids = fields.Many2many('account.invoice', 'p3_id', 'i3_id', '未完成认领其他应收',
                                              compute='compute_invoice_advance')
    yjzy_type = fields.Selection([('sale', '销售'),
                                 ('purchase', '采购'),
                                 ('back_tax', '退税')], u'发票类型')
    renling_type = fields.Selection([('yshxd', '应收认领'),
                                 ('ysrld', '预收认领'),
                                 ('back_tax', '退税认领'),('other_payment', '其他认领')], u'认领属性')


    def apply(self):
        self.ensure_one()
        self.create_yshxd_ysrl()

    def create_yshxd_ysrl(self):
        if self.renling_type in ['yshxd','back_tax'] :
            invoice_attribute = 'normal'
        elif self.renling_type == 'other_paymnet':
            invoice_attribute = 'other_payment'
        else:
            invoice_attribute = False

        yjzy_type = self.yjzy_type
        yshxd_obj = self.env['account.reconcile.order']
        sfk_type = 'yshxd'
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        if self.renling_type in ['yshxd','back_tax','other_payment']:
            yshxd_id = yshxd_obj.create({
                                         'name': name,
                                         'operation_wizard': '10',
                                         'partner_id': self.partner_id.id,
                                         'sfk_type': 'yshxd',
                                         'payment_type': 'inbound',
                                         'partner_type': 'customer',
                                         'yjzy_payment_id':self.yjzy_payment_id.id,
                                         'be_renling': True,
                                         'invoice_attribute': invoice_attribute,
                                         'yjzy_type': yjzy_type
                                         })

            form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_new').id
            return {
                'name': '应收认领单',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.reconcile.order',
                'views': [(form_view, 'form')],
                'res_id': yshxd_id.id,
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': {'default_sfk_type': 'yshxd',
                            'active_id': yshxd_id.id,
                            'bank_amount': 1,
                            'show_so': 1,
                            }

            }




#####################################################################################################################
