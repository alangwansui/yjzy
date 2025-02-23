import base64
import logging
import psycopg2
import smtplib

from email.utils import formataddr
from odoo import _, api, fields, models, tools, SUPERUSER_ID
from odoo.addons.base.ir.ir_mail_server import MailDeliveryException
from odoo.tools.safe_eval import safe_eval


_logger = logging.getLogger(__name__)


class mail_mail(models.Model):
    _inherit = 'mail.mail'

    compose_id = fields.Many2one('mail.compose.message', u'底稿', related='mail_message_id.compose_id', store=True)
    recipient_cc_ids = fields.Many2many('res.partner', 'mail_mail_cc_res_partner_rel', 'mail_mail_id', 'partner_id', u'抄送')
    recipient_bcc_ids = fields.Many2many('res.partner', 'mail_mail_bcc_res_partner_rel', 'mail_mail_id', 'partner_id', u'密送')
    readed = fields.Boolean('客户已打开')
    read_log_ids = fields.One2many('mail.read.log', 'mail_id', '客户读取记录')
    need_return_notification = fields.Boolean('需要回执')
    need_have_read_img = fields.Boolean('发送打开统计标记', default=True)

    @api.multi
    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None):
        IrMailServer = self.env['ir.mail_server']
        for mail_id in self.ids:
            try:
                mail = self.browse(mail_id)
                if mail.state != 'outgoing':
                    if mail.state != 'exception' and mail.auto_delete:
                        mail.sudo().unlink()
                    continue
                # TDE note: remove me when model_id field is present on mail.message - done here to avoid doing it multiple times in the sub method
                if mail.model:
                    model = self.env['ir.model']._get(mail.model)[0]
                else:
                    model = None
                if model:
                    mail = mail.with_context(model_name=model.name)

                # load attachment binary data with a separate read(), as prefetching all
                # `datas` (binary field) could bloat the browse cache, triggerring
                # soft/hard mem limits with temporary data.
                attachments = [(a['datas_fname'], base64.b64decode(a['datas']), a['mimetype'])
                               for a in mail.attachment_ids.sudo().read(['datas_fname', 'datas', 'mimetype'])]

                # specific behavior to customize the send email for notified partners
                email_list = []
                if mail.email_to:
                    email_list.append(mail.send_get_email_dict())


                # for partner in mail.recipient_ids:
                #     email_list.append(mail.send_get_email_dict(partner=partner))

                if True:#mail.cc_visible:
                    email_cc_list = []
                    for partner_cc in mail.recipient_cc_ids:
                        email_to = formataddr((partner_cc.name or 'False', partner_cc.email or 'False'))
                        email_cc_list.append(email_to)
                    # Convert Email List To String For BCC & CC
                    email_cc_string = ','.join(email_cc_list)
                else:
                    email_cc_string = ''

                if True: #mail.bcc_visible:
                    email_bcc_list = []
                    for partner_bcc in mail.recipient_bcc_ids:
                        email_to = formataddr((partner_bcc.name or 'False', partner_bcc.email or 'False'))
                        email_bcc_list.append(email_to)
                    # Convert Email List To String For BCC & CC
                    email_bcc_string = ','.join(email_bcc_list)
                else:
                    email_bcc_string = ''

                # headers
                headers = {}
                ICP = self.env['ir.config_parameter'].sudo()
                bounce_alias = ICP.get_param("mail.bounce.alias")
                catchall_domain = ICP.get_param("mail.catchall.domain")

                #需要回执
                if mail.need_return_notification:
                    headers['Disposition-Notification-To'] = mail.email_from

                if bounce_alias and catchall_domain:
                    if mail.model and mail.res_id:
                        headers['Return-Path'] = '%s+%d-%s-%d@%s' % (bounce_alias, mail.id, mail.model, mail.res_id, catchall_domain)
                    else:
                        headers['Return-Path'] = '%s+%d@%s' % (bounce_alias, mail.id, catchall_domain)
                if mail.headers:
                    try:
                        headers.update(safe_eval(mail.headers))
                    except Exception:
                        pass

                # Writing on the mail object may fail (e.g. lock on user) which
                # would trigger a rollback *after* actually sending the email.
                # To avoid sending twice the same email, provoke the failure earlier
                mail.write({
                    'state': 'exception',
                    'failure_reason': _('Error without exception. Probably due do sending an email without computed recipients.'),
                })
                mail_sent = False

                # Update notification in a transient exception state to avoid concurrent
                # update in case an email bounces while sending all emails related to current
                # mail record.
                notifs = self.env['mail.notification'].search([
                    ('is_email', '=', True),
                    ('mail_message_id', 'in', mail.mapped('mail_message_id').ids),
                    ('res_partner_id', 'in', mail.mapped('recipient_ids').ids),
                    ('email_status', 'not in', ('sent', 'canceled'))
                ])
                if notifs:
                    notifs.sudo().write({
                        'email_status': 'exception',
                    })

                # build an RFC2822 email.message.Message object and send it without queuing
                res = None
                #print('==========wwww======',email_list)
                for email in email_list:









                    body = email.get('body')
                    if mail.need_have_read_img:
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        readed_tag = '<img style="display:none;"  src="%s/mail_mail/have_read/%s"/>' % (base_url, self.id)
                        body += readed_tag



                    msg = IrMailServer.build_email(
                        email_from=mail.email_from,
                        email_to=email.get('email_to'),
                        subject=mail.subject,
                        #body=  email.get('body') + readed_tag,
                        body=body,
                        body_alternative=email.get('body_alternative'),
                        #email_cc=tools.email_split_and_format(email_cc_string),
                        #<jon> 邮件确保cc 来自文本，所有partner_cc 都会预选转为email_cc 传入
                        email_cc=tools.email_split_and_format(mail.email_cc),

                        email_bcc=tools.email_split_and_format(email_bcc_string),
                        reply_to=mail.reply_to,
                        attachments=attachments,
                        message_id=mail.message_id,
                        references=mail.references,
                        object_id=mail.res_id and ('%s-%s' % (mail.res_id, mail.model)),
                        subtype='html',
                        subtype_alternative='plain',
                        headers=headers)
                    try:
                        res = IrMailServer.send_email(
                            msg, mail_server_id=mail.mail_server_id.id, smtp_session=smtp_session)
                    except AssertionError as error:
                        if str(error) == IrMailServer.NO_VALID_RECIPIENT:
                            # No valid recipient found for this particular
                            # mail item -> ignore error to avoid blocking
                            # delivery to next recipients, if any. If this is
                            # the only recipient, the mail will show as failed.
                            _logger.info("Ignoring invalid recipients for mail.mail %s: %s",
                                         mail.message_id, email.get('email_to'))
                        else:
                            raise
                if res:
                    mail.write({'state': 'sent', 'message_id': res, 'failure_reason': False})
                    mail_sent = True

                # /!\ can't use mail.state here, as mail.refresh() will cause an error
                # see revid:odo@openerp.com-20120622152536-42b2s28lvdv3odyr in 6.1
                if mail_sent:
                    _logger.info('Mail with ID %r and Message-Id %r successfully sent', mail.id, mail.message_id)
                mail._postprocess_sent_message(mail_sent=mail_sent)
            except MemoryError:
                # prevent catching transient MemoryErrors, bubble up to notify user or abort cron job
                # instead of marking the mail as failed
                _logger.exception(
                    'MemoryError while processing mail with ID %r and Msg-Id %r. Consider raising the --limit-memory-hard startup option',
                    mail.id, mail.message_id)
                raise
            except (psycopg2.Error, smtplib.SMTPServerDisconnected):
                # If an error with the database or SMTP session occurs, chances are that the cursor
                # or SMTP session are unusable, causing further errors when trying to save the state.
                _logger.exception(
                    'Exception while processing mail with ID %r and Msg-Id %r.',
                    mail.id, mail.message_id)
                raise
            except Exception as e:
                failure_reason = tools.ustr(e)
                _logger.exception('failed sending mail (id: %s) due to %s', mail.id, failure_reason)
                mail.write({'state': 'exception', 'failure_reason': failure_reason})
                mail._postprocess_sent_message(mail_sent=False)
                if raise_exception:
                    if isinstance(e, AssertionError):
                        # get the args of the original error, wrap into a value and throw a MailDeliveryException
                        # that is an except_orm, with name and value as arguments
                        value = '. '.join(e.args)
                        raise MailDeliveryException(_("Mail Delivery Failed"), value)
                    raise

            if auto_commit is True:
                self._cr.commit()
        return True

