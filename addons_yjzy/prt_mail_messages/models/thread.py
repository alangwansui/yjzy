
from odoo import _, api, exceptions, fields, models, tools, SUPERUSER_ID
import logging
from odoo.tools import pycompat, ustr
from odoo.exceptions import MissingError, AccessError

_logger = logging.getLogger(__name__)

TREE_VIEW_ID = False
FORM_VIEW_ID = False

# List of forbidden models
FORBIDDEN_MODELS = ['mail.channel']

# Search for 'ghost' models is performed
GHOSTS_CHECKED = False



###############
# Mail.Thread #
###############
class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    # -- Add context to unlink
    @api.multi
    def unlink(self):
        return super(MailThread, self.with_context(force_delete=True)).unlink()

    @api.multi
    @api.returns('self', lambda value: value.id)
    def message_post(self, body='', subject=None, message_type='notification', subtype=None, parent_id=False, attachments=None,content_subtype='html', **kwargs):
        """
        1：发送消息的数据创建过程
        """

        #print('====MailThread post=====1', kwargs);
        if attachments is None:
            attachments = {}
        if self.ids and not self.ensure_one():
            raise exceptions.Warning(_('Invalid record set: should be called as model (without records) or on single-record recordset'))

        # if we're processing a message directly coming from the gateway, the destination model was
        # set in the context.
        model = False
        if self.ids:
            self.ensure_one()
            model = self._context.get('thread_model', False) if self._name == 'mail.thread' else self._name
            if model and model != self._name and hasattr(self.env[model], 'message_post'):
                RecordModel = self.env[model].with_context(thread_model=None)  # TDE: was removing the key ?
                return RecordModel.browse(self.ids).message_post(
                    body=body, subject=subject, message_type=message_type,
                    subtype=subtype, parent_id=parent_id, attachments=attachments,
                    content_subtype=content_subtype, **kwargs)

        # 0: Find the message's author, because we need it for private discussion
        author_id = kwargs.get('author_id')
        if author_id is None:  # keep False values
            author_id = self.env['mail.message']._get_default_author().id

        # 1: Handle content subtype: if plaintext, converto into HTML
        if content_subtype == 'plaintext':
            body = tools.plaintext2html(body)

        # 2: Private message: add recipients (recipients and author of parent message) - current author
        #   + legacy-code management (! we manage only 4 and 6 commands)
        partner_ids = set()
        kwargs_partner_ids = kwargs.pop('partner_ids', [])
        for partner_id in kwargs_partner_ids:
            if isinstance(partner_id, (list, tuple)) and partner_id[0] == 4 and len(partner_id) == 2:
                partner_ids.add(partner_id[1])
            if isinstance(partner_id, (list, tuple)) and partner_id[0] == 6 and len(partner_id) == 3:
                partner_ids |= set(partner_id[2])
            elif isinstance(partner_id, pycompat.integer_types):
                partner_ids.add(partner_id)
            else:
                pass  # we do not manage anything else
        if parent_id and not model:
            parent_message = self.env['mail.message'].browse(parent_id)
            private_followers = set([partner.id for partner in parent_message.partner_ids])
            if parent_message.author_id:
                private_followers.add(parent_message.author_id.id)
            private_followers -= set([author_id])
            partner_ids |= private_followers

        # 4: mail.message.subtype
        subtype_id = kwargs.get('subtype_id', False)
        if not subtype_id:
            subtype = subtype or 'mt_note'
            if '.' not in subtype:
                subtype = 'mail.%s' % subtype
            subtype_id = self.env['ir.model.data'].xmlid_to_res_id(subtype)

        # automatically subscribe recipients if asked to
        if self._context.get('mail_post_autofollow') and self.ids and partner_ids:
            partner_to_subscribe = partner_ids
            if self._context.get('mail_post_autofollow_partner_ids'):
                partner_to_subscribe = [p for p in partner_ids if p in self._context.get('mail_post_autofollow_partner_ids')]
            self.message_subscribe(list(partner_to_subscribe), force=False)

        # _mail_flat_thread: automatically set free messages to the first posted message
        MailMessage = self.env['mail.message']
        if self._mail_flat_thread and model and not parent_id and self.ids:
            messages = MailMessage.search(['&', ('res_id', '=', self.ids[0]), ('model', '=', model), ('message_type', '=', 'email')], order="id ASC", limit=1)
            if not messages:
                messages = MailMessage.search(['&', ('res_id', '=', self.ids[0]), ('model', '=', model)], order="id ASC", limit=1)
            parent_id = messages and messages[0].id or False
        # we want to set a parent: force to set the parent_id to the oldest ancestor, to avoid having more than 1 level of thread
        elif parent_id:
            messages = MailMessage.sudo().search([('id', '=', parent_id), ('parent_id', '!=', False)], limit=1)
            # avoid loops when finding ancestors
            processed_list = []
            if messages:
                message = messages[0]
                while (message.parent_id and message.parent_id.id not in processed_list):
                    processed_list.append(message.parent_id.id)
                    message = message.parent_id
                parent_id = message.id

        values = kwargs

        #print('====MailThread post=====1.2', [(4, pid) for pid in partner_ids], values.get('partner_cc_ids'))

        personal_author = self.env['personal.partner'].search([('partner_id', '=', author_id)], limit=1)
        values.update({
            'author_id': author_id,
            'model': model,
            'res_id': model and self.ids[0] or False,
            'body': body,
            'subject': subject or False,
            'message_type': message_type,
            'parent_id': parent_id,
            'subtype_id': subtype_id,
            'partner_ids': [(4, pid) for pid in partner_ids],
            'email_to': values.get('email_to') or values.get('to'),
            'email_cc': values.get('email_cc') or values.get('cc'),
            'partner_cc_ids': values.get('partner_cc_ids') or False,
            'personal_partner_ids': values.get('personal_partner_ids') and [(4, pid) for pid in values.get('personal_partner_ids')] or False,
            'personal_partner_cc_ids': values.get('personal_partner_cc_ids') and [(4, pid) for pid in values.get('personal_partner_cc_ids')] or False,
            'personal_author_id': personal_author.id,

        })

        #print('====MailThread post=====1.2.1', values)

        #raise Exception('xxx')

        # 3. Attachments
        #   - HACK TDE FIXME: Chatter: attachments linked to the document (not done JS-side), load the message
        attachment_ids = self._message_post_process_attachments(attachments, kwargs.pop('attachment_ids', []), values)
        values['attachment_ids'] = attachment_ids

        # Avoid warnings about non-existing fields
        for x in ('from', 'to', 'cc'):
            values.pop(x, None)

        # Post the message
        #print('====MailThread post=====2', self._context,  values.get('partner_cc_ids'), values.get('partner_ids'))

        if self._context.get('fetchmail_server_id'):
            values.update({'fetchmail_server_id': self._context.get('fetchmail_server_id')})


        #print('====message ready to 0 create=====', self.env.context, values)
        new_message = MailMessage.create(values)
        #print('====MailThread post=====3',   new_message, new_message.subject)
        #print(self.env['mail.mail'].search([('mail_message_id', '=', new_message.id)], ))


        # Post-process: subscribe author, update message_last_post
        # Note: the message_last_post mechanism is no longer used.  This
        # will be removed in a later version.
        if (self._context.get('mail_save_message_last_post') and
                model and model != 'mail.thread' and self.ids and subtype_id):
            subtype_rec = self.env['mail.message.subtype'].sudo().browse(subtype_id)
            if not subtype_rec.internal:
                # done with SUPERUSER_ID, because on some models users can post only with read access, not necessarily write access
                self.sudo().write({'message_last_post': fields.Datetime.now()})
        if author_id and model and self.ids and message_type != 'notification' and not self._context.get('mail_create_nosubscribe'):
            self.message_subscribe([author_id], force=False)

        self._message_post_after_hook(new_message)

        #print('====MailThread post=====4 end ',  new_message.partner_ids)
        return new_message