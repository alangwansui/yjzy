# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp
from lxml import etree

class RealInvoice(models.Model):
    _name = 'real.invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '实际发票认证'
    _order = 'id desc'

    # @api.depends('partner_id')
    # def compute_invoice_ids(self):
    #     for one in self:
    #         if one.partner_id:
    #             invoice_ids = self.env['account.invoice'].search([('partner_id','=',one.partner_id.id),('state','in',['open','paid'])],limit=100)
    #             one.invoice_ids = invoice_ids

    @api.depends('partner_id')
    def compute_certification_invoice_ids(self):
        if self.state == '05':
            invoice_ids = self.env['account.invoice'].search(
                [('partner_id', '=', self.partner_id.id), ('type','=','in_invoice'),('state', 'in', ['open', 'paid']),('state_2','not in',['50_certified','90_cancel'])], )
            # akiny参考
            res = []
            for one in invoice_ids:
                res.append((0, 0, {
                    'invoice_id': one.id,
                    'amount': one.amount_total,
                    'state': '05'
                }))
            self.certification_invoice_ids = res






    name = fields.Char('编号', default=lambda self: self.env['ir.sequence'].next_by_code('real.invoice'))
    partner_id = fields.Many2one('res.partner',u'合作伙伴')
    line_ids = fields.One2many('real.invoice.line','real_invoice_id',u'明细行')

    state = fields.Selection([('05',u'未开始认证'),('10',u'开始认证'),('20','完成认证'),('refused',u'已拒绝'),('cancel',u'取消')],'State', default='05',)
    currency_id = fields.Many2one('res.currency',string='货币',default=lambda self: self.env.user.company_id.currency_id)
    company_currency_id = fields.Many2one('res.currency', string='公司货币', related='company_id.currency_id',  readonly=True)
    company_id = fields.Many2one('res.company', string='Company',required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    certification_invoice_ids = fields.One2many('sys.invoice.line','real_invoice_id',u'认证账单',compute=compute_certification_invoice_ids,store=True)
    # invoice_ids = fields.Many2many('account.invoice',u'待认证账单',)compute=compute_invoice_ids


    def unlink(self):
        if self.state != '05':
            raise Warning('认证中，不允许删除')
        else:
            return super(RealInvoice, self).unlink()

    def action_state(self):
        line_ids = self.line_ids
        line_20_ids = self.line_ids.filtered(lambda x: x.state == '20')

        if len(line_20_ids) == 0:
            self.state = '05'
        elif len(line_20_ids) == len(line_ids):
            self.state = '20'
            # state_line_no_20_ids.unlink()
        else:
            self.state = '10'

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        # invoice_ids = self.env['account.invoice'].search(
        #     [('partner_id', '=', self.partner_id.id), ('state', 'in', ['open', 'paid'])],)
        # #akiny参考
        # res = []
        # for one in invoice_ids:
        #     res.append((0, 0, {
        #         'invoice_id': one.id,
        #         'amount':one.amount_total,
        #         'state':'05'
        #     }))
        # self.certification_invoice_ids = res

        if self.line_ids:
            raise Warning('已经添加认证发票，无法更换供应商，请先删除认证发票')

        # certification_invoice_obj = self.env['sys.invoice.line']
            # certification_invoice_obj.create({'real_invoice_id': self.id,
            #                                   'invoice_id': one.id,
            #                                   'amount': one.amount_total,
            #                                 })


    # def create_real_invoice_line(self):
    #     invoice_ids = self.invoice_ids.filtered(lambda x : x.certifying == False)
    #     real_invoice_line_id = self.line_ids.filtered(lambda x : x.certifying == False)
    #     certification_invoice_obj = self.env['sys.invoice.line']
    #     for one in invoice_ids:
    #         certification_invoice_obj.create({'real_invoice_id': self.id,
    #                                           'invoice_id': one.id,
    #                                           'amount':one.amount_total,
    #                                           'real_invoice_line_id':real_invoice_line_id,})
    #     return True



class RealInvoiceLine(models.Model):
    _name = 'real.invoice.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '实际发票明细'
    _order = 'id desc'

    @api.depends('certification_invoice_ids','certification_invoice_ids.amount')
    def compute_certification_amount(self):
        for one in self:
            certification_amount = sum(x.amount for x in one.certification_invoice_ids)
            one.certification_amount = certification_amount

    name = fields.Char('编号', default=lambda self: self.env['ir.sequence'].next_by_code('real.invoice.line'))
    real_invoice_id = fields.Many2one('real.invoice',u'实际发票认证单', ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company',
                                 related='real_invoice_id.company_id', store=True, readonly=True, related_sudo=False)
    certification_invoice_ids = fields.One2many('sys.invoice.line','real_invoice_line_id',u'认证账单')
    state = fields.Selection([('05','未开始认证'),('10',u'等待认证'),('20','已认证')],u'状态',default='05')
    real_invoice_date = fields.Date(u'日期',default=lambda self: fields.date.today())
    real_invoice_partner = fields.Many2one('res.partner',u'合作伙伴',related='real_invoice_id.partner_id')
    currency_id = fields.Many2one('res.currency',u'货币',related='real_invoice_id.currency_id')
    certification_amount = fields.Monetary('认证金额',currency_field='currency_id',compute=compute_certification_amount)
    amount = fields.Monetary('金额',currency_field='currency_id')
    type = fields.Selection([('sale',u'销售发票'),('purchase',u'进项发票')],'发票类型', default='purchase')


    def unlink(self):
        if self.state != '05':
            raise Warning('认证中，不允许删除')
        else:
            return super(RealInvoiceLine, self).unlink()

    @api.multi
    def name_get(self):
        result = []
        for one in self:
            name = one.name
            result.append((one.id,name))
        return result

    # @api.onchange('certifying')
    # def onchange_certifying(self):
    #     # if self.certifying:
    #     #     self.state='10'
    #     # else:
    #     #     self.state='05'
    #     #     print('self.certification_invoice_ids',self.certification_invoice_ids)
    #     for one in self.certification_invoice_ids:
    #         print('one.real_invoice_line_id',one.real_invoice_line_id)
    #
    #         print('one.real_invoice_line_id', one.real_invoice_line_id)
    #         one.state = '05'
    #         one.certifying = False
    #         print('action_test', one.state)
    #         # one.real_invoice_line_id = False
    #         # one.onchange_certifying()

    def action_certified(self):
        if self.state=='10':
            self.state = '20'
            for one in self.certification_invoice_ids:
                one.state ='20'
                one.invoice_id.state_2 = '50_certified'
        self.real_invoice_id.action_state()

    def action_certifying(self):
        if self.state == '05':
            self.state = '10'
        self.real_invoice_id.action_state()

    def action_no_certifying(self):
        if self.state == '10':
            self.state = '05'

        for one in self.certification_invoice_ids:
            # one.write({'state': '05'})

            one.state = '05'

            one.real_invoice_line_id = False
        self.real_invoice_id.action_state()







    def action_confirm_certification(self):
        self.state = '20'
        for one in self.certification_invoice_ids:
            one.state_2 = '50_certified'



class SysInvoiceLine(models.Model):
    _name = 'sys.invoice.line'

    _description = '认证的账单'
    _order = 'id desc'

    real_invoice_id = fields.Many2one('real.invoice', u'实际发票认证单', required=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.invoice',u'发票', required=True, ondelete='restrict')
    real_invoice_line_id = fields.Many2one('real.invoice.line',u'实际发票')
    company_id = fields.Many2one('res.company', string='Company',
                                 related='real_invoice_id.company_id', store=True, readonly=True, related_sudo=False)
    date = fields.Date(u'日期')
    currency_id = fields.Many2one('res.currency',u'货币',related='real_invoice_id.currency_id')
    amount = fields.Monetary('账单金额',currency_field='currency_id')
    state = fields.Selection([('05','未开始认证'),('10',u'等待认证'),('15','部分认证'),('20','已认证')],u'状态')


    # @api.onchange('certifying')
    # def onchange_certifying(self):
    #     print('real_invoice_line_akiny', self.certifying)
    #     if self.certifying:
    #         real_invoice_line = self.real_invoice_id.line_ids.filtered(lambda x: x.state == '10')
    #         print('real_invoice_line_akiny',real_invoice_line)
    #         if not real_invoice_line:
    #             self.certifying = False
    #             self.state = '05'
    #             self.real_invoice_line_id = False
    #         else:
    #             self.real_invoice_line_id = real_invoice_line
    #             self.state = '10'
    #     else:
    #         self.state='05'
    #         self.real_invoice_line_id = False




    def action_certifying(self):
        real_invoice_line = self.real_invoice_id.line_ids.filtered(lambda x: x.state == '10')
        print('len(real_invoice_line)',len(real_invoice_line))
        if len(real_invoice_line) >1:
            raise Warning('大于一张实际发票正在被认证，请先取消一张！')
        elif len(real_invoice_line) == 0:
            raise Warning('请先开启一张需要被认证的实际发票！')
        else:
            self.real_invoice_line_id = real_invoice_line
            self.state = '10'
        self.real_invoice_id.action_state()

    def action_no_certifying(self):
        real_invoice_line = self.real_invoice_line_id
        if not real_invoice_line and real_invoice_line.state == '20':
            raise Warning('不允许关闭认证！')
        else:
            self.state = '05'
            self.real_invoice_line_id = False
        self.real_invoice_id.action_state()



        # if not real_invoice_line:
        #     self.certifying = False
        #     self.state = '05'
        #     self.real_invoice_line_id = False
        # else:













#####################################################################################################################
