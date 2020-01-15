from odoo import models, fields, api, _, tools, SUPERUSER_ID, registry
from odoo.tools.misc import split_every
import logging
from odoo.exceptions import MissingError, AccessError

_logger = logging.getLogger(__name__)


################
# Res.Partner #
################
class PRTPartner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"

    messages_from_count = fields.Integer(string="Messages From", compute='_messages_from_count')
    messages_to_count = fields.Integer(string="Messages To", compute='_messages_to_count')


    def make_personal_partner(self):
        for one in self:
            pass


    @api.model
    def _notify_send(self, body, subject, recipients, **mail_values):
        #<jon email create function>
        print('================_notify_send========================', mail_values.get('email_to'),  mail_values)
        emails = self.env['mail.mail']
        recipients_nbr = len(recipients)
        for email_chunk in split_every(50, recipients.ids):
            # TDE FIXME: missing message parameter. So we will find mail_message_id
            # in the mail_values and browse it. It should already be in the
            # cache so should not impact performances.
            mail_message_id = mail_values.get('mail_message_id')
            message = self.env['mail.message'].browse(mail_message_id) if mail_message_id else None
            #print('=============_notify_send======2==', message)

            if message and message.model and message.res_id and message.model in self.env and hasattr(self.env[message.model], 'message_get_recipient_values'):
                print('=============_notify_send======2.1==')
                tig = self.env[message.model].browse(message.res_id)
                print('=============_notify_send======2.1.1==', tig)
                recipient_values = tig.message_get_recipient_values(notif_message=message, recipient_ids=email_chunk)
            else:
                print('=============_notify_send======2.2==')
                recipient_values = self.env['mail.thread'].message_get_recipient_values(notif_message=None, recipient_ids=email_chunk)

            #print('=============_notify_send======3==', recipient_values)
            create_values = {
                'body_html': body,
                'subject': subject,
                'email_to': message.email_to,
                'email_cc': message.email_cc,

            }
            # Set Partner CC & BCC Value In Recipient CC & BCC
            if True: #message.cc_visible:
                create_values.update({'recipient_cc_ids': [(4, pccid.id) for pccid in message.partner_cc_ids]})
            else:
                create_values.update({'recipient_cc_ids': []})

            if True:#message.bcc_visible:
                create_values.update({'recipient_bcc_ids': [(4, pbccid.id) for pbccid in message.partner_bcc_ids]})
            else:
                create_values.update({'recipient_bcc_ids': []})

            #print('======mail.mail create at here 1========', recipient_values['email_to'], create_values['email_to'])

            create_values.update(mail_values)
            #<jon> 如果消息中已经存在email_to， 不要替换掉
            if (not create_values.get('email_to')) and recipient_values.get('email_to'):
                create_values.update(recipient_values)

            #print('======mail.mail create at here ========', recipient_values['email_to'], create_values['email_to'])

            emails |= self.env['mail.mail'].create(create_values)
        return emails, recipients_nbr

# -- Count messages from
    @api.depends('message_ids')
    @api.multi
    def _messages_from_count(self):
        for rec in self:
            if rec.id:
                rec.messages_from_count = self.env['mail.message'].search_count([('author_id', 'child_of', rec.id),
                                                                                 ('message_type', '!=', 'notification'),
                                                                                 ('model', '!=', 'mail.channel')])
            else:
                rec.messages_from_count = 0

# -- Count messages from
    @api.depends('message_ids')
    @api.multi
    def _messages_to_count(self):
        for rec in self:
            rec.messages_to_count = self.env['mail.message'].search_count([('partner_ids', 'in', [rec.id]),
                                                                           ('message_type', '!=', 'notification'),
                                                                           ('model', '!=', 'mail.channel')])

# -- Open related
    @api.multi
    def partner_messages(self):
        self.ensure_one

        # Choose what messages to display
        open_mode = self._context.get('open_mode', 'from')

        if open_mode == 'from':
            domain = [('message_type', '!=', 'notification'),
                      ('author_id', 'child_of', self.id),
                      ('model', '!=', 'mail.channel')]
        else:
            domain = [('message_type', '!=', 'notification'),
                      ('partner_ids', 'in', [self.id]),
                      ('model', '!=', 'mail.channel')]

        # Cache Tree View and Form View ids
        global TREE_VIEW_ID
        global FORM_VIEW_ID

        if not TREE_VIEW_ID:
            TREE_VIEW_ID = self.env.ref('prt_mail_messages.prt_mail_message_tree').id
            FORM_VIEW_ID = self.env.ref('prt_mail_messages.prt_mail_message_form').id

        return {
            'name': _("Messages"),
            "views": [[TREE_VIEW_ID, "tree"], [FORM_VIEW_ID, "form"]],
            'res_model': 'mail.message',
            'type': 'ir.actions.act_window',
            'context': "{'check_messages_access': True}",
            'target': 'current',
            'domain': domain
        }

# -- Send email from partner's form view
    @api.multi
    def send_email(self):
        self.ensure_one()

        return {
            'name': _("New message"),
            "views": [[False, "form"]],
            'res_model': 'mail.compose.message',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {
                'default_res_id': False,
                'default_parent_id': False,
                'default_model': False,
                'default_partner_ids': [self.id],
                'default_attachment_ids': False,
                'default_is_log': False,
                'default_body': False,
                'default_wizard_mode': 'compose'
            }
        }

    def open_messsage(self):
        self.ensure_one()

        partner_ids = [self.id] + [x.id for x in self.child_ids]
        partner_emails = [self.email] + [x.email for x in self.child_ids]

        msg_obj = self.env['mail.message']




        msg_ids = []
        msg_ids += [x['id'] for x in msg_obj.search_read([('partner_ids', 'in', partner_ids)], ['id'])]
        for em in partner_emails:
            msg_ids += [x['id'] for x in msg_obj.search_read(['|', ('email_to', 'ilike', em), ('manual_to', 'ilike', em)], ['id'])]



        print(msg_ids)



        return {
                    "name": u"消息",
                    "type": "ir.actions.act_window",
                    "view_mode": "tree,form",
                    "res_model": "mail.message",
                    "view_id": "",
                    "domain": [('id', 'in', msg_ids)],
                    "context": {},
        }





