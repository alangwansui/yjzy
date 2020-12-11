# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.addons.account.models.account_payment import account_payment as Account_Payment
from .comm import sfk_type



class account_payment(models.Model):
    _inherit = 'account.payment'

    rckfd_attribute = fields.Selection([('expense',u'费用'),
                                        ('advance_payment', u'预付账款'),
                                        ('yfzk',u'应付账单'),
                                        ('other_payment',u'其他应付款'),
                                        ('expense_po',u'费用转货款'),
                                        ('other_po',u'增加采购应付')],u'付款属性')

    def compute_fkzl_count(self):
        for one in self:
            one.fksqd_2_ids_count = len(one.fksqd_2_ids)
            one.fybg_fkzl_ids_count = len(one.fybg_fkzl_ids)
            one.yfsqd_fkzl_ids_count = len(one.yfsqd_fkzl_ids)
            one.yshx_fkzl_ids_count = len(one.yshx_fkzl_ids)
            one.yshx_fkzl_line_ids_count = len(one.yshx_fkzl_line_ids)


    bank_id_bank = fields.Many2one('res.bank',u'银行名称')
    bank_id_huming = fields.Char('收款账户名', related='bank_id.huming')
    bank_id_kaihuhang = fields.Char(related='bank_id.kaihuhang')
    bank_id_acc_number = fields.Char(related='bank_id.acc_number')

    fkzl_id = fields.Many2one('account.payment',u'付款指令',)#ondelete="restrict"
    fksqd_2_ids = fields.One2many('account.payment','fkzl_id',u'付款申请单',domain=[('sfk_type','=','rcfkd'),('state_fkzl','in',['05_fksq','07_post_fkzl','30_done'])])#domain=[('sfk_type','=','fksqd')]
    fksqd_2_ids_count = fields.Integer('付款申请单数量',compute=compute_fkzl_count)

    fybg_fkzl_ids = fields.One2many('hr.expense.sheet', 'fkzl_id', u'费用报告')
    fybg_fkzl_ids_count = fields.Integer('费用报告数量', compute=compute_fkzl_count)
    expense_fkzl_ids =  fields.One2many('hr.expense', 'fkzl_id', u'费用明细')
    yfsqd_fkzl_ids = fields.One2many('account.payment', 'fkzl_id', u'预付申请单',domain=[('sfk_type','=','yfsqd')])
    yfsqd_fkzl_ids_count = fields.Integer('预付申请单数量', compute=compute_fkzl_count)
    yshx_fkzl_ids = fields.One2many('account.reconcile.order', 'fkzl_id', u'应收付认领单')
    yshx_fkzl_ids_count = fields.Integer('应收付认领单数量', compute=compute_fkzl_count)
    yshx_fkzl_line_ids = fields.One2many('account.reconcile.order.line.no','fkzl_id',u'应付明细')
    yshx_fkzl_line_ids_count = fields.Integer('应收付认领单数量', compute=compute_fkzl_count)
    def create_fkzl(self):
        if len(self.mapped('partner_id')) > 1:
            raise Warning('不同对象不允许一起付款！')
        if len(self.mapped('bank_id')) > 1:
            raise Warning('不同的收款账户不允许一起付款！')
        if len(self.mapped('fk_journal_id')) > 1:
            raise Warning('不同的付款账户不允许一起付款！')
        sfk_type = 'fkzl'
        if sfk_type:
            name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        else:
            name = None
        account_code = '112301'
        advance_account = self.env['account.account'].search(
            [('code', '=', account_code), ('company_id', '=', self[0].company_id.id)], limit=1)
        amount = sum(x.amount for x in self)
        fkzl_obj = self.env['account.payment']
        if not self[0].journal_id.currency_id:
            raise Warning(u'没有取到付款日记账的货币，请检查设置')
        if not advance_account:
            raise Warning(u'没有找到对应的预处理科目%s' % account_code)
        fkzl_id = fkzl_obj.create({
            'name':name,
            'sfk_type':sfk_type,
            'payment_type': 'outbound',
            'partner_id': self[0].partner_id.id,
            'partner_type': 'supplier',
            'journal_id': self[0].journal_id.id,
            'currency_id': self[0].journal_id.currency_id.id,
            'amount': amount,
            'company_id': self[0].company_id.id,
            'payment_method_id': 2,
            'advance_ok': True,
            'advance_account_id': advance_account.id,
            'bank_id': self[0].bank_id.id,
            'include_tax': self[0].include_tax,

        })

        for one in self:
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
                        'only_name':1,
                        'display_name_code':1,

                        }
        }


    def open_wizard_fkzl(self):
        if len(self.mapped('partner_id')) > 1:
            raise Warning('不同对象不允许一起付款！')
        if len(self.mapped('bank_id')) > 1:
            raise Warning('不同的收款账户不允许一起付款！')
        if len(self.mapped('fk_journal_id')) > 1:
            raise Warning('不同的付款账户不允许一起付款！')
        sfk_type = 'fkzl'
        # if sfk_type:
        #     name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        # else:
        #     name = None
        account_code = '112301'
        advance_account = self.env['account.account'].search(
            [('code', '=', account_code), ('company_id', '=', self[0].company_id.id)], limit=1)
        amount = sum(x.amount for x in self)
        fybg_ids = []
        expense_ids = []
        yfsqd_ids = []
        yshx_ids = []
        yshxline_ids = []
        rcfkd_ids = []
        for one in self:
            rcfkd_ids.append(one.id)
            if one.fybg_ids:
                for x in one.fybg_ids:
                    fybg_ids.append(x.id)
            if one.expense_ids:
                for x in one.expense_ids:
                    expense_ids.append(x.id)
            if one.yfsqd_ids:
                for x in one.yfsqd_ids:
                    yfsqd_ids.append(x.id)
            if one.yshx_ids:
                for x in one.yshx_ids:
                    yshx_ids.append(x.id)
                    for line in x.line_no_ids:
                        yshxline_ids.append(line.id)

        yshx_ids_1 = [[6, 0, yshx_ids]]
        print('test_akiy',fybg_ids,expense_ids,yfsqd_ids,yshx_ids)
        fkzl_obj = self.env['wizard.fkzl']
        if not self[0].journal_id.currency_id:
            raise Warning(u'没有取到付款日记账的货币，请检查设置')
        if not advance_account:
            raise Warning(u'没有找到对应的预处理科目%s' % account_code)#参考
        fkzl_id = fkzl_obj.with_context({'default_yshx_ids_new':yshx_ids,'yfsqd_ids':yfsqd_ids,'default_rcfkd_ids':rcfkd_ids,'default_expense_ids':expense_ids,
                                         'default_fybg_ids': fybg_ids,'default_yshx_ids_line_no':yshxline_ids}).create({
            # 'name': name,
            'sfk_type': sfk_type,
            'partner_id': self[0].partner_id.id,
            'journal_id': self[0].journal_id.id,
            'currency_id': self[0].journal_id.currency_id.id,
            'amount': amount,
            'company_id': self[0].company_id.id,
            'advance_account_id': advance_account.id,
            'bank_id': self[0].bank_id.id,
            'include_tax': self[0].include_tax,
            # 'yshx_ids':yshx_ids



        })

        form_view = self.env.ref('yjzy_extend.wizard_fkzl')
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'wizard.fkzl',
            'views': [(form_view.id, 'form')],
            'res_id': fkzl_id.id,
            'target': 'new',
            'context': {

                        }
        }

    #支付完成
    def action_fkzl_approve(self):
        today = fields.date.today()
        self.write({'post_uid': self.env.user.id,
                    'post_date': today,
                    })
        self.post()
        self.compute_balance()

    def action_hegui_refuse(self, reason):
        self.write({'state_1': '80_refused',
                    'state_fkzl': '80_refused',
                    })
        for tb in self:
            tb.message_post_with_view('yjzy_extend.payment_template_refuse_reason',
                                      values={'reason': reason, 'name': self.name},
                                      subtype_id=self.env.ref(
                                          'mail.mt_note').id)  # 定义了留言消息的模板，其他都可以参考，还可以继续参考费用发送计划以及邮件方式


