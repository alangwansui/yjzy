# -*- coding: utf-8 -*-
import logging
import base64
from email._parseaddr import AddrlistClass
from datetime import  datetime, timedelta
from email.utils import formataddr, parseaddr
from email.header import Header
from odoo import models, fields, api, _, tools, SUPERUSER_ID
from odoo.exceptions import Warning
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF

def multi_parseaddr(s):
    res = []
    if s:
        for x in s.split(','):
            res.append(parseaddr(x))
    return res


_logger = logging.getLogger(__name__)


########################
# Mail.Compose Message #
########################
class PRTMailComposer(models.Model):
    _inherit = 'mail.compose.message'

    @api.depends('message_ids')
    def compute_message_count(self):
        for one in self:
            one.message_count = len(one.message_ids)

    @api.depends('mail_ids', 'message_ids', 'mail_ids.state')
    def compute_mail(self):
        for one in self:
            one.message_count = len(one.message_ids)
            one.mail_count = len(one.mail_ids)
            one.is_sent = any([x.state == 'sent' for x in one.mail_ids])

    @api.model
    def default_get(self, field_list):
        ctx = self.env.context
        res = super(PRTMailComposer, self).default_get(field_list)

        if not ctx.get('default_model'):
            channel = self.env['mail.channel'].search([('sent_uid', '=', self.env.user.id)], limit=1)
            if not channel:
                channel = self.env['mail.channel'].search([('name', '=', ctx.get('use_channel_name', ''))], limit=1)

            if channel:
                res.update({
                    'model': 'mail.channel',
                    'res_id': channel.id,
                })

        if (not 'wizard_mode' in ctx) and (not ctx.get('default_body')):
            res.update({
                'body': self.env.user.signature,
            })

        return res


    @api.depends('personal_partner_ids', 'personal_partner_cc_ids', 'personal_author_id', 'partner_ids', 'partner_cc_ids')
    def compute_compose_all_partner(self):
        for one in self:
            if self._name != 'mail.compose.message':
                continue

            all_partners = one.partner_cc_ids | one.partner_ids
            all_personal = one.personal_author_id | one.personal_partner_ids | one.personal_partner_cc_ids

            one.all_partner_ids = all_partners
            one.all_personal_ids = all_personal


    wizard_mode = fields.Char(string="Wizard mode")
    forward_ref = fields.Reference(string="Attach to record", selection='_referenceable_models_fwd', readonly=False)
    message_ids = fields.One2many('mail.message', 'compose_id', u'发送的消息')
    message_count = fields.Integer(u'消息数', compute=compute_mail, store=True)
    mail_ids = fields.One2many('mail.mail', 'compose_id', u'发送的邮件')
    mail_count = fields.Integer(u'邮件数', compute=compute_mail, store=True)
    is_sent = fields.Boolean(u'是否发送成功', compute=compute_mail, store=True, index=True)
    message_type = fields.Selection(default="email")
    partner_cc_ids = fields.Many2many('res.partner', 'mail_compose_message_cc_res_partner_rel', 'wizard_id', 'partner_id', u'抄送')
    partner_bcc_ids = fields.Many2many('res.partner', 'mail_compose_message_bcc_res_partner_rel', 'wizard_id', 'partner_id', u'密送')

    manual_to = fields.Char(u'收件人2')
    manual_cc = fields.Char(u'抄送2')

    force_notify_email = fields.Boolean(u'强制使用邮件发送')
    last_send_time = fields.Datetime('最后发送时间')


    personal_partner_ids = fields.Many2many('personal.partner', 'ref_personal_compose', 'cid', 'pid',  u'收件人:通讯录')
    personal_partner_cc_ids = fields.Many2many('personal.partner', 'refcc_personal_compose', 'cid', 'pid',  u'抄送:通讯录')
    personal_author_id = fields.Many2one('personal.partner', u'作者:通讯录')

    all_partner_ids = fields.Many2many('res.partner', 'ref_compose_all_partner', 'pid', 'mid',  u'所有伙伴', compute=compute_compose_all_partner, store=True)
    all_personal_ids = fields.Many2many('personal.partner', 'ref_compose_all_personal', 'personal_id', 'partner_id',  u'所有通讯录', compute=compute_compose_all_partner, store=True)


    @api.model
    def cron_create_personal(self, domain=None):
        for one in self.search([]).filtered(lambda x: x._name == 'mail.compose.message'):
            if one.email_to:
                one.personal_partner_ids |= one.parse_address_make_personal(one.email_to)
            if one.email_cc:
                one.personal_partner_cc_ids |= one.parse_address_make_personal(one.email_cc)


    def parse_address_make_personal(self, addrss):
        print('==parse_address_make_personal==', addrss)
        user = self.create_uid
        personal_obj = self.env['personal.partner']
        default_tag = self.env.ref('prt_mail_messages.personal_tag_income_tmp')
        records = self.env['personal.partner']


        for name, addr in AddrlistClass(addrss).getaddrlist():
            if not ('@' in addr):
                continue
            print('==parse_address_make_personal==', name, addr, user.id)
            addr = addr.lower()
            personal = personal_obj.search([('email', '=', addr),('user_id', '=', user.id)])
            if not personal:
                personal = personal_obj.create({
                    'name': name,
                    'email': addr,
                    'user_id': user.id,
                    'tag_id': default_tag.id,
                })
            records |= personal
        return records


    @api.onchange('personal_partner_ids')
    def onchange_personal_partner(self):
        email_to = ', '.join(['%s' % p.display_name for p in self.personal_partner_ids])
        self.email_to = email_to

    @api.onchange('personal_partner_cc_ids')
    def onchange_personal_partner_cc(self):
        email_cc = ', '.join(['%s' % p.display_name for p in self.personal_partner_cc_ids])
        self.email_cc = email_cc


    def mail_address_check(self):
        self.ensure_one()
        


    def recompute_mail_address(self):
        self.ensure_one()

        email_to = self.email_to or ''
        email_cc= self.email_cc or ''


        list_to = multi_parseaddr(email_to)
        list_cc = multi_parseaddr(email_cc)

        list_to_email = [x[1] for x in list_to]
        list_cc_email = [x[1] for x in list_cc]

        for p in self.partner_ids:
            if p.email not in list_to_email:
                if email_to:
                    email_to += ',%s' % formataddr((p.display_name, p.email))
                else:
                    email_to +=  '%s' % formataddr( (p.display_name, p.email))

        for p in self.partner_cc_ids:
            if p.email not in list_cc_email:
                if email_cc:
                    email_cc += ',%s' % formataddr((p.display_name, p.email))
                else:
                    email_cc +=  '%s' % formataddr( (p.display_name, p.email))

        self.email_to = email_to
        self.email_cc = email_cc

    @api.multi
    def send_mail_button(self):
        self.ensure_one()

        if self.last_send_time:
            print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>', (datetime.now() - datetime.strptime(self.last_send_time, DTF)).seconds)
            if (datetime.now() - datetime.strptime(self.last_send_time, DTF)).seconds < 5:
                raise Warning(u'请勿重复发送')
            else:
                self.last_send_time = fields.datetime.now()
                self.send_mail()

        else:
            self.last_send_time = fields.datetime.now()
            self.send_mail()

        #发送后，通讯录放入正式组
        personals = self.personal_partner_ids | self.personal_partner_cc_ids
        out_tmp_personals = personals.filtered(lambda x: x.tag_id.code == 'out_tmp')
        if out_tmp_personals:
            normal_tag = self.env.ref('prt_mail_messages.personal_tag_normal')
            out_tmp_personals.write({'tag_id': normal_tag.id})

        #<jon> 标记为已经回复
        ctx = self.env.context
        if ctx.get('is_reply'):
            org_msg = self.env['mail.message'].browse(ctx.get('active_id'))
            org_msg.had_replied = True

        wizard = self.env['wizard.compose.action'].create({
            'compose_id': self.id,
        })

        return {
            'name': '邮件发送完成',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.compose.action',
            'res_id': wizard.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }




    @api.multi
    def get_mail_values(self, res_ids):
        """Generate the values that will be used by send_mail to create mail_messages
        or mail_mails. """
        self.ensure_one()
        results = dict.fromkeys(res_ids, False)
        rendered_values = {}
        mass_mail_mode = self.composition_mode == 'mass_mail'

        # render all template-based value at once
        if mass_mail_mode and self.model:
            rendered_values = self.render_message(res_ids)
        # compute alias-based reply-to in batch
        reply_to_value = dict.fromkeys(res_ids, None)
        if mass_mail_mode and not self.no_auto_thread:
            # reply_to_value = self.env['mail.thread'].with_context(thread_model=self.model).browse(res_ids).message_get_reply_to(default=self.email_from)
            reply_to_value = self.env['mail.thread'].with_context(thread_model=self.model).message_get_reply_to(res_ids, default=self.email_from)

        for res_id in res_ids:
            # static wizard (mail.message) values
            mail_values = {
                'subject': self.subject,
                'body': self.body or '',
                'parent_id': self.parent_id and self.parent_id.id,
                'partner_ids': [partner.id for partner in self.partner_ids],
                'attachment_ids': [attach.id for attach in self.attachment_ids],
                'partner_cc_ids': [partner_cc.id for partner_cc in self.partner_cc_ids],
                'partner_bcc_ids': [partner_bcc.id for partner_bcc in self.partner_bcc_ids],

                'recipient_cc_ids':[partner_cc.id for partner_cc in self.partner_cc_ids],
                'recipient_bcc_ids':[partner_bcc.id for partner_bcc in self.partner_bcc_ids],

                'email_to': self.email_to,
                'manual_to': self.manual_to,

                'email_cc': self.email_cc,
                'author_id': self.author_id.id,
                'email_from': self.email_from,
                'record_name': self.record_name,
                'no_auto_thread': self.no_auto_thread,
                'mail_server_id': self.mail_server_id.id,
                'mail_activity_type_id': self.mail_activity_type_id.id,
                'force_notify_email': self.force_notify_email,
                'personal_partner_ids': [x.id for x in self.personal_partner_ids],
                'personal_partner_cc_ids': [x.id for x in self.personal_partner_cc_ids],

            }

            #print('=1212====',mail_values['email_to'],  [partner_cc.id for partner_cc in self.partner_cc_ids], mail_values)
            #print('>>>>>>>>', mass_mail_mode, self.model)
            # mass mailing: rendering override wizard static values
            if mass_mail_mode and self.model:
                if self.model in self.env and hasattr(self.env[self.model], 'message_get_email_values'):
                    mail_values.update(self.env[self.model].browse(res_id).message_get_email_values())
                # keep a copy unless specifically requested, reset record name (avoid browsing records)
                mail_values.update(notification=not self.auto_delete_message, model=self.model, res_id=res_id, record_name=False)
                # auto deletion of mail_mail
                if self.auto_delete or self.template_id.auto_delete:
                    mail_values['auto_delete'] = True
                # rendered values using template
                email_dict = rendered_values[res_id]
                mail_values['partner_ids'] += email_dict.pop('partner_ids', [])
                mail_values.update(email_dict)
                if not self.no_auto_thread:
                    mail_values.pop('reply_to')
                    if reply_to_value.get(res_id):
                        mail_values['reply_to'] = reply_to_value[res_id]
                if self.no_auto_thread and not mail_values.get('reply_to'):
                    mail_values['reply_to'] = mail_values['email_from']
                # mail_mail values: body -> body_html, partner_ids -> recipient_ids
                mail_values['body_html'] = mail_values.get('body', '')
                mail_values['recipient_ids'] = [(4, id) for id in mail_values.pop('partner_ids', [])]

                # process attachments: should not be encoded before being processed by message_post / mail_mail create
                mail_values['attachments'] = [(name, base64.b64decode(enc_cont)) for name, enc_cont in email_dict.pop('attachments', list())]
                attachment_ids = []
                for attach_id in mail_values.pop('attachment_ids'):
                    new_attach_id = self.env['ir.attachment'].browse(attach_id).copy({'res_model': self._name, 'res_id': self.id})
                    attachment_ids.append(new_attach_id.id)
                mail_values['attachment_ids'] = self.env['mail.thread']._message_preprocess_attachments(
                    mail_values.pop('attachments', []),
                    attachment_ids, 'mail.message', 0)

            results[res_id] = mail_values

        print('---get_mail_vale------', results)
        return results

    def save_action(self):
        return True

    @api.model
    def _referenceable_models_fwd(self):
        return [(x.object, x.name) for x in self.env['res.request.link'].sudo().search([])]

    @api.onchange('forward_ref')
    @api.multi
    def ref_change(self):
        self.ensure_one()
        if self.forward_ref:
            self.update({
                'model': self.forward_ref._name,
                'res_id': self.forward_ref.id
            })

    @api.model
    def get_record_data(self, values):
        """
        Copy-pasted mail.compose.message original function so stay aware in case it is changed in Odoo core!

        Returns a defaults-like dict with initial values for the composition
        wizard when sending an email related a previous email (parent_id) or
        a document (model, res_id). This is based on previously computed default
        values. """
        result = {}
        subj = self._context.get('default_subject', False)
        subject = tools.ustr(subj) if subj else False
        ctx = self.env.context
        if not subject:
            if values.get('parent_id'):
                parent = self.env['mail.message'].browse(values.get('parent_id'))

                #print('==parent==', parent)

                result['record_name'] = parent.record_name,
                subject = tools.ustr(parent.subject or parent.record_name or '')
                if not values.get('model'):
                    result['model'] = parent.model
                if not values.get('res_id'):
                    result['res_id'] = parent.res_id

                #<jon> cancel partner_ids add 
                # partner_ids = values.get('partner_ids', list()) + \
                #               [(4, id) for id in
                #                parent.partner_ids.filtered(lambda rec: rec.email not in [self.env.user.email, self.env.user.company_id.email]).ids]
                # if self._context.get('is_private') and parent.author_id:  # check message is private then add author also in partner list.
                #     partner_ids += [(4, parent.author_id.id)]
                # result['partner_ids'] = partner_ids


            elif values.get('model') and values.get('res_id'):

                #print('====================================', ctx )
                if ctx.get('wizard_mode', '') == 'forward':
                    msg = self.env[ctx.get('active_model')].browse(ctx.get('active_id'))
                    result['record_name'] = msg.subject
                    subject = tools.ustr(msg.subject)

                else:
                    doc_name_get = self.env[values.get('model')].browse(values.get('res_id')).name_get()
                    result['record_name'] = doc_name_get and doc_name_get[0][1] or ''
                    subject = tools.ustr(result['record_name'])




            # Change prefix in case we are forwarding
            re_prefix = _('Fwd:') if self._context.get('default_wizard_mode', False) == 'forward' else _('Re:')

            if subject and not (subject.startswith('Re:') or subject.startswith(re_prefix)):
                subject = "%s %s" % (re_prefix, subject)

        result['subject'] = subject

        return result
