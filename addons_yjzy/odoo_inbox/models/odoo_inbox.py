# -*- coding: utf-8 -*-
import email
import base64
import werkzeug
import logging
import requests
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from odoo.exceptions import RedirectWarning, UserError

import odoo
from odoo import api, fields, models, _
from odoo.addons.google_account import TIMEOUT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.http import request
from datetime import date, datetime, timedelta

_logger = logging.getLogger(__name__)

HEADERS = {'Content-type': 'application/json'}

class OdooInbox(models.AbstractModel):
    _name = 'odoo.inbox'

    # def get_gmail_scope(self):
    #     return 'https://www.googleapis.com/auth/gmail.modify'

    # def authorize_google_uri(self, from_url='http://www.odoo.com'):
    #     url = self.env['google.service']._get_authorize_uri(from_url, self.STR_SERVICE, scope=self.get_calendar_scope())
    #     return url

    # def get_last_sync_date(self):
    #     ir_config = self.env['ir.config_parameter'].sudo()
    #     lastSync = ir_config.get_param('gmail_last_sync_date')
    #     date_after = lastSync and lastSync or date.today()
    #     ir_config.set_param('gmail_last_sync_date', date.today())
    #     return (fields.Date.from_string(str(date_after))-timedelta(days=1)).strftime('%Y/%m/%d')

    # @api.model
    # def get_threads(self):
    #     MailMessage = self.env['mail.message'].sudo()
    #     service = request.session.get('gr').build_service()
    #     try:
    #         user_id = self.env.user
    #         content = service.users().messages().list(userId=user_id.gmail_user_id, q="after: %s" % (self.get_last_sync_date())).execute()
    #         if content.get('messages'):
    #             for msg in content['messages']:
    #                 existing_msg_ids = MailMessage.search([('message_id', '=', msg.get('id'))])
    #                 if not existing_msg_ids:
    #                     message = service.users().messages().get(userId=user_id.gmail_user_id, id=msg['id'],
    #                             format='raw').execute()
    #                     mail = self.create_odoo_message(message, user_id , 'inbox')
    #             return content
    #     except requests.HttpError as error:
    #         raise UserError(_('An error occurred: While Getting Threads %s') % error)
    #     return True

    # @api.model
    # def get_drafts(self):
    #     MailMessage = self.env['mail.message'].sudo()
    #     service = request.session.get('gr').build_service()
    #     try:
    #         user_id = self.env.user
    #         response = service.users().drafts().list(userId=user_id.gmail_user_id).execute()
    #         if response.get('drafts'):
    #             drafts = response['drafts']
    #             for draft in drafts:
    #                 existing_msg_ids = MailMessage.search([('draft_message_id', '=', draft.get('id'))])
    #                 message = service.users().messages().get(userId=user_id.gmail_user_id, id=draft.get('message').get('id'),
    #                         format='raw').execute()
    #                 message.update({'draft_message_id': draft.get('id')})
    #                 if not existing_msg_ids:
    #                     self.create_odoo_message(message, user_id, 'draft')
    #             return drafts
    #         return
    #     except errors.HttpError as error:
    #         raise UserError(_('An error occurred: %s') % error)

    # @api.model
    # def create_odoo_message(self, message=None, user_id=None, label=None):
    #     MailMessage = self.env['mail.message'].sudo()
    #     if not message:
    #         return
    #     msg_str = base64.urlsafe_b64decode(message['raw'].encode('ASCII')) if message.get('raw') else False
    #     if msg_str:
    #         mime_msg = email.message_from_string(msg_str) if msg_str else False
    #         msg_dict = self.env['mail.thread'].message_parse(mime_msg)
    #         msg_dict['message_id'] = message.get('id')
    #         msg_dict['draft_message_id'] = message.get('draft_message_id')
    #         # msg_dict['gmail'] = True
    #         msg_dict['author_id'] = user_id.partner_id.id
    #         msg_dict['record_name'] = msg_dict.get('subject')
    #         gmail_lables = message.get('labelIds')
    #         if gmail_lables and 'SENT' in gmail_lables:
    #             msg_dict['author_id'] = request.env.user.partner_id.id
    #         elif gmail_lables and 'TRASH' in gmail_lables:
    #             msg_dict['message_label'] = 'trash'
    #         else:
    #             msg_dict['message_label'] = label

    #         msg_dict['msg_unread'] = gmail_lables and 'UNREAD' in gmail_lables or False
    #         if msg_dict.get('message_id'):
    #             existing_msg_ids = MailMessage.search([('message_id', '=', msg_dict.get('message_id'))])
    #             if existing_msg_ids:
    #                 _logger.info('Ignored mail from %s to %s with Message-Id %s: found duplicated Message-Id during processing', msg_dict.get('from'), msg_dict.get('to'), msg_dict.get('message_id'))
    #                 return False
    #         mail = MailMessage.create(msg_dict)
    #         if msg_dict.get('attachments'):
    #             mail.attachment_ids = request.env['mail.thread']._message_preprocess_attachments(msg_dict.get('attachments'), [], mail._name, mail.id)
    #         return mail


    @api.multi
    def set_done(self, message=None):
        message.message_label = 'done'

    @api.multi
    def set_star(self, action=None, message=None):
        message.message_label = 'starred' if action == 'add' else 'inbox'

    @api.multi
    def move_to_send(self, action=None, message=None):
        message.message_label = 'sent' if action == 'add' else 'inbox'

    @api.multi
    def move_to_trash(self, message=None):
        message.message_label = 'trace'
        # ir_config = self.env['ir.config_parameter'].sudo()
        # service = request.session.get('gr').build_service()
        # try:
        #     user_id = self.env.user
        #     content = service.users().messages().trash(id=message.message_id).execute()
        #     message.message_label = 'trash'
        #     raise UserError(_("Message with id: %s has been trashed.") % (content['id']))
        #     return message
        # except errors.HttpError as error:
        #     raise UserError(_('An error occurred: %s') % error)


    # @api.model
    # def move_to_trash(self, message=None):
    #     ir_config = self.env['ir.config_parameter'].sudo()
    #     service = request.session.get('gr').build_service()
    #     try:
    #         user_id = self.env.user
    #         content = service.users().messages().trash(id=message.message_id).execute()
    #         message.message_label = 'trash'
    #         raise UserError(_("Message with id: %s has been trashed.") % (content['id']))
    #         return message
    #     except errors.HttpError as error:
    #         raise UserError(_('An error occurred: %s') % error)

    # @api.model
    # def toggle_read(self, message=None):
    #     if not message.msg_unread:
    #         return
    #     message.msg_unread = False
    #     service = request.session.get('gr').build_service()
    #     try:
    #         user_id = self.env.user
    #         message = service.users().messages().modify(userId=user_id.gmail_user_id, id=message.message_id, body={'removeLabelIds':  ['UNREAD']}).execute()
    #         raise UserError(_('Message ID: %s - With Label IDs %s') % (message['id'],message['labelIds']))
    #         return message
    #     except requests.HttpError as error:
    #         raise UserError(_('An error occurred: %s') % error)

    # @api.model
    # def compose_message(self, data):
    #     partner_to = self.env['res.partner'].browse(data.get('partners_list'))
    #     user_id = self.env.user
    #     message = MIMEMultipart()
    #     partners_emails = [','.join(map(str, partner_to.mapped('email')))]
    #     message_to = partners_emails[0] + ',' + str(data.get('to')) if partners_emails else str(data.get('to'))
    #     message['to'] = message_to
    #     message['cc'] = data.get('cc')
    #     message['from'] = user_id.gmail_user_id
    #     message['subject'] = data.get('subject')
    #     msg = MIMEText(data.get('body'), 'html')
    #     message.attach(msg)
    #     attach = data.get('attachments_list')
    #     for attachment in attach:
    #         if hasattr(attachment, 'filename'):
    #             content_type = attachment.content_type
    #             main_type, sub_type = content_type.split('/', 1)
    #             if main_type == 'text':
    #                 msg = MIMEText(attachment.read(), _subtype=sub_type)
    #             elif main_type == 'image':
    #                 msg = MIMEImage(attachment.read(), _subtype=sub_type)
    #             elif main_type == 'audio':
    #                 msg = MIMEAudio(attachment.read(), _subtype=sub_type)
    #             else:
    #                 msg = MIMEBase(main_type, sub_type)
    #                 msg.set_payload(attachment.read())
    #             msg.add_header('Content-Disposition', 'attachment', filename=attachment.filename)
    #             message.attach(msg)
    #     service = request.session.get('gr').build_service()
    #     try:
    #         send = (service.users().messages().send(userId=user_id.gmail_user_id, body={'raw': base64.urlsafe_b64encode(message.as_string())})
    #                    .execute())
    #         message = service.users().messages().get(userId=user_id.gmail_user_id, id=send['id'],
    #                     format='raw').execute()
    #         self.create_gmail_message(message, user_id, 'sent')
    #         print 'Message Id: %s' % message['id']
    #         return message
    #     except errors.HttpError, error:
    #         print 'An error occurred: %s' % error

