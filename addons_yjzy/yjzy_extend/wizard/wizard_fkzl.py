# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.addons.account.models.account_payment import account_payment as Account_Payment
from addons_yjzy.yjzy_extend.models.comm import sfk_type

class wizard_fkzl(models.TransientModel):
    _name = 'wizard.fkzl'


    def compute_count(self):
        for one in self:
            one.expense_ids_count = len(one.expense_ids)
            one.yfsqd_ids_count = len(one.yfsqd_ids)
            one.yshx_ids_line_no_count = len(one.yshx_ids_line_no)

    rcfkd_ids = fields.Many2many('account.payment','ref_rec_rcfkd', 'rcfkd_id', 'zl_id',u'付款申请单')
    partner_id = fields.Many2one('res.partner',u'合作伙伴')
    journal_id = fields.Many2one('account.journal', string='Payment Journal',)
    currency_id = fields.Many2one('res.currency', string='Currency',)
    company_id = fields.Many2one('res.company',  string='Company', )
    bank_id = fields.Many2one('res.partner.bank', u'银行账号')
    bank_id_huming = fields.Char(related='bank_id.huming')
    bank_id_kaihuhang = fields.Char(related='bank_id.kaihuhang')
    bank_id_acc_number = fields.Char(related='bank_id.acc_number')
    include_tax = fields.Boolean(u'是否含税')
    name = fields.Char(u'编号', )
    sfk_type = fields.Selection(sfk_type, u'收付类型')
    amount = fields.Monetary(string='Payment Amount', )
    fybg_ids = fields.Many2many('hr.expense.sheet','ref_rec_fybg', 'fybg_id', 'zl_id',)
    expense_ids = fields.Many2many('hr.expense','ref_rec_expense', 'expense_id', 'zl_id',)
    expense_ids_count = fields.Integer('费用明细数量',compute=compute_count)
    yfsqd_ids = fields.Many2many('account.payment','ref_rec_yfsqd', 'yfsqd_id', 'zl_id',)
    yfsqd_ids_count = fields.Integer('预收数量', compute=compute_count)
    yshx_ids = fields.Many2many('account.payment','ref_rec_yshx', 'yshx_id', 'zl_id',)
    yshx_ids_new = fields.Many2many('account.reconcile.order', 'ref_rec_yshx_new', 'yshx_new_id', 'zl_id', )

    yshx_ids_line_no = fields.Many2many('account.reconcile.order.line.no', 'ref_rec_yshx_line', 'yshx_line_id', 'zl_id', )
    yshx_ids_line_no_count = fields.Integer('应付明细数量', compute=compute_count)

    advance_account_id = fields.Many2one('account.account',
                                         string=u"预付科目",


                                         help="This account will be used instead of the default one as the receivable account for the current partner")





    def apply(self):
        self.ensure_one()
        ctx = self.env.context
        sfk_type = self.sfk_type
        if sfk_type:
            name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        else:
            name = None
        advance_account_id = self.advance_account_id
        amount = self.amount
        fkzl_obj = self.env['account.payment']
        if not self.journal_id.currency_id:
            raise Warning(u'没有取到付款日记账的货币，请检查设置')
        if not advance_account_id:
            raise Warning(u'没有找到对应的预处理科目%s' % advance_account_id)
        fkzl_id = fkzl_obj.create({
            'name': name,
            'sfk_type': sfk_type,
            'payment_type': 'outbound',
            'partner_id': self.partner_id.id,
            'partner_type': 'supplier',
            'journal_id': self.journal_id.id,
            'currency_id': self.journal_id.currency_id.id,
            'amount': amount,
            'company_id': self.company_id.id,
            'payment_method_id': 2,
            'advance_ok': True,
            'advance_account_id': advance_account_id.id,
            'bank_id': self.bank_id.id,
            'include_tax': self.include_tax,

        })

        for one in self.rcfkd_ids:
            one.fkzl_id = fkzl_id
            if one.fybg_ids:
                for x in one.fybg_ids:
                    x.fkzl_id = fkzl_id
            if one.expense_ids:
                for x in one.expense_ids:
                    x.fkzl_id = fkzl_id
            if one.yfsqd_ids:
                for x in one.yfsqd_ids:
                    x.fkzl_id = fkzl_id
            if one.yshx_ids:
                for x in one.yshx_ids:

                    x.fkzl_id = fkzl_id
                    print('x_akiny', x)
                    x.action_to_fkzl()
                    for yingfurld in x.reconcile_payment_ids:
                        yingfurld.fkzl_id = fkzl_id
                    for line_no in x.line_no_ids:
                        line_no.fkzl_id = fkzl_id

            one.state_fkzl = '07_post_fkzl'

        form_view = self.env.ref('yjzy_extend.view_fkzl_form')
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'views': [(form_view.id, 'form')],
            'res_id': fkzl_id.id,
            'target': 'current',
            'context': {'default_sfk_type': 'fkzl',
                        'only_name': 1,
                        'display_name_code': 1,

                        }
        }





#####################################################################################################################
