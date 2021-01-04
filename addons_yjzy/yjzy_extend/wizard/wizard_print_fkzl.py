# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.addons.account.models.account_payment import account_payment as Account_Payment
from addons_yjzy.yjzy_extend.models.comm import sfk_type

class wizard_print_fkzl(models.TransientModel):
    _name = 'wizard.print.fkzl'



    fkzl_id = fields.Many2one('account.payment',u'付款指令')
    print_times = fields.Integer(u'打印次数')
    print_date = fields.Datetime('打印时间')
    print_uid = fields.Many2one('res.users', u'最新打印人员')
    is_print = fields.Boolean('是否已经打印',default=False)

    def apply(self):
        self.ensure_one()
        if self.is_print:
            return True
        today = fields.datetime.now()
        uid = self.env.user.id
        print_times = self.print_times
        print_times_last = print_times + 1
        self.fkzl_id.write({'print_date': today,
                    'print_uid': uid,
                    'can_print': False,
                    'print_times': print_times_last})
        self.is_print = True
        return  self.env.ref('yjzy_extend.action_report_fkzl').report_action(self)

        # form_view = self.env.ref('yjzy_extend.view_fkzl_form')
        # return {
        #     'type': 'ir.actions.act_window',
        #     'view_mode': 'form',
        #     'res_model': 'account.payment',
        #     'views': [(form_view.id, 'form')],
        #     'res_id': fkzl_id.id,
        #     'target': 'current',
        #     'context': {'default_sfk_type': 'fkzl',
        #                 'only_name': 1,
        #                 'display_name_code': 1,
        #
        #                 }
        # }





#####################################################################################################################
