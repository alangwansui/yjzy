from odoo import models, fields, api, _


class wizard_compose_action(models.TransientModel):
    _name = 'wizard.compose.action'

    compose_id = fields.Many2one('mail.compose.message', u'撰稿')

    def open_message_out(self):
        tree_view = self.env.ref('prt_mail_messages.prt_mail_message_out_tree')
        form_view = self.env.ref('prt_mail_messages.prt_mail_message_out_form')
        return {
            'name': '发件箱',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'mail.message',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('message_type', '=', 'email'), ('compose_id', '=', self.compose_id.id)],
        }
