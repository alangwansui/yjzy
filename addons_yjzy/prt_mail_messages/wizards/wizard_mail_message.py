from odoo import models, fields, api, _


class wizard_mail_message(models.TransientModel):
    _name = 'wizard.mail.message'
    _description = '邮件操作'


    def apply(self):
        ctx = self.env.context
        print('===', ctx)
        ctx

        messages = self.env['mail.message'].browse(ctx.get('active_ids'))


        messages.write({'state_delete': ctx.get('to_state_delete')})



