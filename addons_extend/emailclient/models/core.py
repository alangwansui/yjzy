# -*- coding: utf-8 -*-

#########################################################################

import re
import smtplib
import poplib
import imaplib
import base64
import string
import email
import time
import datetime
from imapclient import IMAPClient
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import decode_header, Header
from email.utils import formatdate
from odoo import api, models, fields, _, tools
from odoo.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)


def parser_header(s):
    print('===parser_header==', s)
    res = ''
    for content, charset in decode_header(s):
        _logger.info('=====parser_header, %s  %s' % (content, charset))
        if charset != None:
            c = content.decode(charset)
        else:
            if isinstance(content, bytes):
                c = content.decode('ascii')
            if isinstance(content, str):
                c = content
        res += c
    return res

class poweremail_core_accounts(models.Model):
    """Email Accounts"""
    _name = "poweremail.core_accounts"
    _description = 'Email Accounts'

    _known_content_types = [
        'multipart/mixed',
        'multipart/alternative',
        'multipart/related',
        'text/plain',
        'text/html',
    ]

    name = fields.Char('Name', size=64, required=True, readonly=True, select=True, states={'draft': [('readonly', False)]})
    user = fields.Many2one('res.users', 'Related User', required=True, readonly=True, states={'draft': [('readonly', False)]})
    email_id = fields.Char('Email ID', size=120, required=True, readonly=True, states={'draft': [('readonly', False)]})
    smtpserver = fields.Char('Server', size=120, required=True, readonly=True, states={'draft': [('readonly', False)]})
    smtpport = fields.Integer('SMTP Port', size=64, required=True, readonly=True, states={'draft': [('readonly', False)]})
    smtpuname = fields.Char('User Name', size=120, required=False, readonly=True, states={'draft': [('readonly', False)]})
    smtppass = fields.Char('Password', size=120, required=False, readonly=True, states={'draft': [('readonly', False)]})
    smtptls = fields.Boolean('Use TLS', readonly=True, states={'draft': [('readonly', False)]}, )
    smtpssl = fields.Boolean('Use SSL/TLS (only in python 2.6)', readonly=True, states={'draft': [('readonly', False)]})
    send_pref = fields.Selection([('html', 'HTML otherwise Text'),
                                  ('text', 'Text otherwise HTML'),
                                  ('both', 'Both HTML & Text'),
                                  ], 'Mail Format', required=True)
    iserver = fields.Char('Incoming Server', size=100, readonly=True, states={'draft': [('readonly', False)]})
    isport = fields.Integer('Port', readonly=True, states={'draft': [('readonly', False)]}, )
    isuser = fields.Char('User Name', size=100, readonly=True, states={'draft': [('readonly', False)]})
    ispass = fields.Char('Password', size=100, readonly=True, states={'draft': [('readonly', False)]})
    iserver_type = fields.Selection([('imap', 'IMAP'), ('pop3', 'POP3')], 'Server Type', readonly=True, states={'draft': [('readonly', False)]})
    isssl = fields.Boolean('Use SSL', readonly=True, states={'draft': [('readonly', False)], })
    isfolder = fields.Char('Folder', readonly=True, size=100)
    last_mail_id = fields.Integer('Last Downloaded Mail', readonly=False)
    rec_headers_den_mail = fields.Boolean('First Receive headers, then download mail')
    dont_auto_down_attach = fields.Boolean('Dont Download attachments automatically')
    allowed_groups = fields.Many2many('res.groups', 'account_group_rel', 'templ_id', 'group_id', string="Allowed User Groups")
    company = fields.Selection([('yes', 'Yes'), ('no', 'No'), ], 'Company Mail A/c', readonly=True, required=True,
                               states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Initiated'),
                              ('suspended', 'Suspended'),
                              ('approved', 'Approved'), ], 'Account Status', required=True, readonly=False, default='draft')

    _sql_constraints = [
        ('email_uniq', 'unique (email_id)', 'Another setting already exists with this email ID !')
    ]

    @api.constrains
    def check_user_company(self, cursor, user, ids):
        if self.company == 'no':
            if self.search_count([('user', '=', user), ('company', '=', 'no')]) > 1:
                raise Warning(u'一个用户只能有一个账号')
        return True

    @api.onchange()
    def on_change_emailid(self, cursor, user, ids, name=None, email_id=None, context=None):
        """
        Called when the email ID field changes.

        UI enhancement
        Writes the same email value to the smtpusername
        and incoming username
        """
        # TODO: Check and remove the write. Is it needed?
        self.write(cursor, user, ids, {'state': 'draft'}, context=context)
        return {
            'value': {
                'state': 'draft',
                'smtpuname': email_id,
                'isuser': email_id
            }
        }

    def _get_outgoing_server(self):
        self.ensure_one()
        print('==_get_outgoing_server==1', self.smtpssl, self.smtpserver, self.smtpport)


        server = smtplib.SMTP_SSL(self.smtpserver, self.smtpport)


        print('==_get_outgoing_server==2', server )
        if self.smtptls:
            server.ehlo()
            server.starttls()
            server.ehlo()
        print('==_get_outgoing_server==3', self.smtpuname, self.smtppass)
        if self.smtpuname and self.smtppass:
            server.login(self.smtpuname, self.smtppass)

        print('==_get_outgoing_server==4')
        return server

    def check_outgoing_connection(self):
        print('=======check_outgoing_connection===')
        try:
            self._get_outgoing_server()
            raise Warning(_("SMTP Test Connection Was Successful"))

        except Exception as error:
            raise Warning(_("Out going connection test failed Reason: %s") % error)

    def _get_imap_server(self):
        """
        @param record: Browse record of current connection
        @return: IMAP or IMAP_SSL object
        """

        if self.isssl:
            serv = imaplib.IMAP4_SSL(self.iserver, self.isport)
        else:
            serv = imaplib.IMAP4(self.iserver, self.isport)
        # Now try to login
        serv.login(self.isuser, self.ispass)
        return serv


    def _get_pop3_server(self):
        """
        @param record: Browse record of current connection
        @return: POP3 or POP3_SSL object
        """

        if self.isssl:
            serv = poplib.POP3_SSL(self.iserver, self.isport)
        else:
            serv = poplib.POP3(self.iserver, self.isport)
        # Now try to login
        serv.user(self.isuser)
        serv.pass_(self.ispass)
        return serv
        raise Exception(
            _("Programming Error in _get_pop3_server method. The record received is invalid.")
        )

    def _get_incoming_server(self):
        """
        Returns the Incoming Server object
        Could be IMAP/IMAP_SSL/POP3/POP3_SSL
        
        @attention: DO NOT USE except_osv IN THIS METHOD
        
        @param cursor: Database Cursor
        @param user: ID of current user
        @param ids: ID/list of ids of current object for
                    which connection is required
                    First ID will be chosen from lists
        @param context: Context
        
        @return: IMAP/POP3 server object or Exception
        """
        self.ensure_one()

        if not self.iserver:
            raise Exception(_("Incoming server is not defined"))
        if not self.isport:
            raise Exception(_("Incoming port is not defined"))
        if not self.isuser:
            raise Exception(_("Incoming server user name is not defined"))
        if not self.isuser:
            raise Exception(_("Incoming server password is not defined"))
        # Now fetch the connection
        if self.iserver_type == 'imap':
            serv = self._get_imap_server()
        elif self.iserver_type == 'pop3':
            serv = self._get_pop3_server()
        return serv


    def check_incoming_connection(self):
        """
        checks incoming credentials and confirms if outgoing connection works
        (Attached to button)
        @param cursor: Database Cursor
        @param user: ID of current user
        @param ids: list of ids of current object for
                    which connection is required
        @param context: Context
        """
        try:
            self._get_incoming_server()
            raise Warning(_("Incoming Test Connection Was Successful"))
        except Warning as success_message:
            raise success_message
        except Exception as error:
            raise Warning( _("Reason: %s") % error)

    def do_approval(self, cr, uid, ids, context={}):
        # TODO: Check if user has rights
        self.write(cr, uid, ids, {'state': 'approved'}, context=context)

    #        wf_service = netsvc.LocalService("workflow")

    def smtp_connection(self, cursor, user, id, context=None):
        """
        This method should now wrap smtp_connection
        """
        # This function returns a SMTP server object
        # logger = netsvc.Logger()
        core_obj = self.browse(cursor, user, id, context)
        if core_obj.smtpserver and core_obj.smtpport and core_obj.state == 'approved':
            try:
                serv = self._get_outgoing_server(cursor, user, id, context)
            except Exception as error:
                logging.getLogger(_("Power Email")).info(
                    _("Mail from Account %s failed on login. Probable Reason: Could not login to server\nError: %s") % (id, error))
                # logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Mail from Account %s failed on login. Probable Reason: Could not login to server\nError: %s") % (id, error))
                return False
            # Everything is complete, now return the connection
            return serv
        else:
            logging.getLogger(_("Power Email")).info(_("Mail from Account %s failed. Probable Reason: Account not approved") % id)
            # logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Mail from Account %s failed. Probable Reason: Account not approved") % id)
            return False

    # **************************** MAIL SENDING FEATURES ***********************#
    def split_to_ids(self, ids_as_str):
        """
        Identifies email IDs separated by separators
        and returns a list
        TODO: Doc this
        "a@b.com,c@bcom; d@b.com;e@b.com->['a@b.com',...]"
        """
        email_sep_by_commas = ids_as_str \
            .replace('; ', ',') \
            .replace(';', ',') \
            .replace(', ', ',')
        return email_sep_by_commas.split(',')

    def get_ids_from_dict(self, addresses={}):
        """
        TODO: Doc this
        """
        result = {'all': []}
        keys = ['To', 'CC', 'BCC']
        for each in keys:
            ids_as_list = self.split_to_ids(addresses.get(each, ''))
            while '' in ids_as_list:
                ids_as_list.remove('')
            result[each] = ids_as_list
            result['all'].extend(ids_as_list)
        return result

    def send_mail(self, cr, uid, ids, addresses, subject='', body=None, payload=None, context=None):
        # TODO: Replace all this crap with a single email object
        if body is None:
            body = {}
        if payload is None:
            payload = {}
        if context is None:
            context = {}
        # logger = netsvc.Logger()
        for id in ids:
            core_obj = self.browse(cr, uid, id, context)
            serv = self.smtp_connection(cr, uid, id)
            if serv:
                try:
                    msg = MIMEMultipart()
                    if subject:
                        msg['Subject'] = subject
                    sender_name = Header(core_obj.name, 'utf-8').encode()
                    msg['From'] = sender_name + " <" + core_obj.email_id + ">"
                    msg['Organization'] = tools.ustr(core_obj.user.company_id.name)
                    msg['Date'] = formatdate()
                    addresses_l = self.get_ids_from_dict(addresses)
                    if addresses_l['To']:
                        msg['To'] = ','.join(addresses_l['To'])
                    if addresses_l['CC']:
                        msg['CC'] = ','.join(addresses_l['CC'])
                    #                    if addresses_l['BCC']:
                    #                        msg['BCC'] = u','.join(addresses_l['BCC'])
                    if body.get('text', False):
                        temp_body_text = body.get('text', '')
                        l = len(temp_body_text.replace(' ', '').replace('\r', '').replace('\n', ''))
                        if l == 0:
                            body['text'] = 'No Mail Message'
                    # Attach parts into message container.
                    # According to RFC 2046, the last part of a multipart message, in this case
                    # the HTML message, is best and preferred.
                    if core_obj.send_pref == 'text' or core_obj.send_pref == 'both':
                        body_text = body.get('text', 'No Mail Message')
                        body_text = tools.ustr(body_text)
                        msg.attach(MIMEText(body_text.encode("utf-8"), _charset='UTF-8'))
                    if core_obj.send_pref == 'html' or core_obj.send_pref == 'both':
                        html_body = body.get('html', '')
                        if len(html_body) == 0 or html_body == '':
                            html_body = body.get('text', '<p>No Mail Message</p>').replace('\n', '<br/>').replace('\r', '<br/>')
                        html_body = tools.ustr(html_body)
                        msg.attach(MIMEText(html_body.encode("utf-8"), _subtype='html', _charset='UTF-8'))
                    # Now add attachments if any
                    for file in list(payload.keys()):
                        part = MIMEBase('application', "octet-stream")
                        part.set_payload(base64.decodestring(payload[file]))
                        part.add_header('Content-Disposition', 'attachment; filename="%s"' % file)
                        encoders.encode_base64(part)
                        msg.attach(part)
                except Exception as error:
                    logging.getLogger(_("Power Email")).info(
                        _("Mail from Account %s failed. Probable Reason: MIME Error\nDescription: %s") % (id, error))
                    # logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Mail from Account %s failed. Probable Reason: MIME Error\nDescription: %s") % (id, error))
                    return error
                try:
                    # print  msg.as_string()
                    serv.sendmail(msg['From'], addresses_l['all'], msg.as_string())
                except Exception as error:
                    logging.getLogger(_("Power Email")).info(
                        _("Mail from Account %s failed. Probable Reason: Server Send Error\nDescription: %s") % (id, error))
                    # logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Mail from Account %s failed. Probable Reason: Server Send Error\nDescription: %s") % (id, error))
                    return error
                # The mail sending is complete
                serv.close()
                logging.getLogger(_("Power Email")).info(_("Mail from Account %s successfully Sent.") % (id))
                # logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("Mail from Account %s successfully Sent.") % (id))
                return True
            else:
                logging.getLogger(_("Power Email")).info(_("Mail from Account %s failed. Probable Reason: Account not approved") % id)
                # logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Mail from Account %s failed. Probable Reason: Account not approved") % id)

    def extracttime(self, time_as_string):
        """
        TODO: DOC THis
        """
        # logger = netsvc.Logger()
        # The standard email dates are of format similar to:
        # Thu, 8 Oct 2009 09:35:42 +0200
        # print time_as_string
        date_as_date = False
        convertor = {'+': 1, '-': -1}
        try:
            time_as_string = time_as_string.replace(',', '')
            date_list = time_as_string.split(' ')
            date_temp_str = ' '.join(date_list[1:5])
            if len(date_list) >= 6:
                sign = convertor.get(date_list[5][0], False)
            else:
                sign = False
            try:
                dt = datetime.datetime.strptime(
                    date_temp_str,
                    "%d %b %Y %H:%M:%S")
            except:
                try:
                    dt = datetime.datetime.strptime(
                        date_temp_str,
                        "%d %b %Y %H:%M")
                except:
                    return False
            if sign:
                try:
                    offset = datetime.timedelta(
                        hours=sign * int(
                            date_list[5][1:3]
                        ),
                        minutes=sign * int(
                            date_list[5][3:5]
                        )
                    )
                except Exception as e2:
                    """Looks like UT or GMT, just forget decoding"""
                    return False
            else:
                offset = datetime.timedelta(hours=0)
            dt = dt + offset
            date_as_date = dt.strftime('%Y-%m-%d %H:%M:%S')
            # print date_as_date
        except Exception as e:
            logging.getLogger(_("Power Email")).info(_("Datetime Extraction failed. Date: %s\nError: %s") % (time_as_string, e))
            # logger.notifyChannel(_("Power Email"),netsvc.LOG_WARNING,_("Datetime Extraction failed. Date: %s\nError: %s") % (time_as_string,e))
        return date_as_date

    def save_header(self, mail, serv_ref):

        context = self.env.context
        mail_obj = self.env['poweremail.mailbox']


        vals = {
            'pem_from': parser_header(mail['From']),
            'pem_to': mail['To'] and self.decode_header_text(mail['To']) or 'no recepient',
            'pem_cc': self.decode_header_text(mail['cc']),
            'pem_bcc': self.decode_header_text(mail['bcc']),
            'pem_recd': mail['date'],
            'date_mail': self.extracttime(mail['date']) or time.strftime("%Y-%m-%d %H:%M:%S"),
            'pem_subject': parser_header(mail['Subject']),
            'server_ref': serv_ref,
            'folder': 'inbox',
            'state': context.get('state', 'unread'),
            'pem_body_text': 'Mail not downloaded...',
            'pem_body_html': 'Mail not downloaded...',
            'pem_account_id': self.id,
        }
        # Identify Mail Type
        if mail.get_content_type() in self._known_content_types:
            vals['mail_type'] = mail.get_content_type()
        else:
            logging.getLogger(_("Power Email")).info(_("Saving Header of unknown payload (%s) Account: %s.") % (mail.get_content_type(), coreaccountid))
            # logger.notifyChannel(_("Power Email"),netsvc.LOG_WARNING,_("Saving Header of unknown payload (%s) Account: %s.") % (mail.get_content_type(),coreaccountid))
        # Create mailbox entry in Mail
        crid = False
        try:
            print('====to create=========', vals)
            one = mail_obj.search([('server_ref', '=', serv_ref),('pem_account_id','=',self.id)], limit=1)
            if not one:
                one = mail_obj.create(vals)
            else:
                print('===邮件已经存在')
        except Exception as e:
            logging.getLogger(_("Power Email")).info(
                _("Save Header -> Mailbox create error. Account: %s, Mail: %s, Error: %s") % (self.id, serv_ref, str(e)))
            # logger.notifyChannel(_("Power Email"),netsvc.LOG_ERROR,_("Save Header -> Mailbox create error. Account: %s, Mail: %s, Error: %s") % (coreaccountid,serv_ref, str(e)))
        # Check if a create was success
        if crid:
            logging.getLogger(_("Power Email")).info(
                _("Header for Mail %s Saved successfully as ID: %s for Account: %s.") % (serv_ref, one.id, self.id))
            # logger.notifyChannel(_("Power Email"),netsvc.LOG_INFO,_("Header for Mail %s Saved successfully as ID: %s for Account: %s.") % (serv_ref, crid, coreaccountid))
            crid = False
            return True
        else:
            logging.getLogger(_("Power Email")).info(_("IMAP Mail -> Mailbox create error. Account: %s, Mail: %s") % (self.id, serv_ref))
            # logger.notifyChannel(_("Power Email"),netsvc.LOG_ERROR,_("IMAP Mail -> Mailbox create error. Account: %s, Mail: %s") % (coreaccountid, serv_ref))

    def save_fullmail(self, mail, serv_ref):
        print('===save_fullmail 1')
        ctx = self.env.context

        mail_obj = self.env['poweremail.mailbox']
        # TODO:If multipart save attachments and save ids
        vals = {
            'pem_from': self.decode_header_text(mail['From']),
            'pem_to': self.decode_header_text(mail['To']),
            'pem_cc': self.decode_header_text(mail['cc']),
            'pem_bcc': self.decode_header_text(mail['bcc']),
            'pem_recd': mail['date'],
            'date_mail': self.extracttime(
                mail['date']
            ) or time.strftime("%Y-%m-%d %H:%M:%S"),
            'pem_subject': self.decode_header_text(mail['subject']),
            'server_ref': serv_ref,
            'folder': 'inbox',
            'state': ctx.get('state', 'unread'),
            'pem_body_text': 'Mail not downloaded...',  # TODO:Replace with mail text
            'pem_body_html': 'Mail not downloaded...',  # TODO:Replace
            'pem_account_id': self.id,
        }
        parsed_mail = self.get_payloads(mail)
        vals['pem_body_text'] = parsed_mail['text']
        vals['pem_body_html'] = parsed_mail['html']
        # Create the mailbox item now
        try:
            one = mail_obj.search([('server_ref', '=', serv_ref),('pem_account_id','=',self.id)], limit=1)
            if not one:
                one = mail_obj.create(vals)
                print('===邮件创建成成')
            else:
                print('===邮件已经存在')
        except Exception as e:
            logging.getLogger(_("Power Email")).info(
                _("Save Header -> Mailbox create error. Account: %s, Mail: %s, Error: %s") % (self.id, serv_ref, str(e)))
            # logger.notifyChannel(_("Power Email"),netsvc.LOG_ERROR,_("Save Header -> Mailbox create error. Account: %s, Mail: %s, Error: %s") % (coreaccountid,serv_ref,str(e)))
        # Check if a create was success
        if one:
            pass
            # if parsed_mail['attachments']:
            #     self.save_attachments(mail, crid, parsed_mail, self.id)

        else:
            pass

        return True

    def complete_mail(self, cr, uid, mail, coreaccountid, serv_ref, mailboxref, context=None):
        if context is None:
            context = {}
        # Internal function for saving of mails to mailbox
        # mail: eMail Object
        # coreaccountid: ID of poeremail core account
        # serv_ref:Mail ID in the IMAP/POP server
        # mailboxref: ID of record in malbox to complete
        # logger = netsvc.Logger()
        mail_obj = self.env('poweremail.mailbox')
        # TODO:If multipart save attachments and save ids
        vals = {
            'pem_from': self.decode_header_text(mail['From']),
            'pem_to': mail['To'] and self.decode_header_text(mail['To']) or 'no recepient',
            'pem_cc': self.decode_header_text(mail['cc']),
            'pem_bcc': self.decode_header_text(mail['bcc']),
            'pem_recd': mail['date'],
            'date_mail': time.strftime("%Y-%m-%d %H:%M:%S"),
            'pem_subject': self.decode_header_text(mail['subject']),
            'server_ref': serv_ref,
            'folder': 'inbox',
            'state': context.get('state', 'unread'),
            'pem_body_text': 'Mail not downloaded...',  # TODO:Replace with mail text
            'pem_body_html': 'Mail not downloaded...',  # TODO:Replace
            'pem_account_id': coreaccountid
        }
        # Identify Mail Type and get payload
        parsed_mail = self.get_payloads(mail)
        vals['pem_body_text'] = tools.ustr(parsed_mail['text'])
        vals['pem_body_html'] = tools.ustr(parsed_mail['html'])
        # Create the mailbox item now
        crid = False
        try:
            crid = mail_obj.write(cr, uid, mailboxref, vals, context)
        except Exception as e:
            logging.getLogger(_("Power Email")).info(_("Save Mail -> Mailbox write error Account: %s, Mail: %s") % (coreaccountid, serv_ref))
            # logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Save Mail -> Mailbox write error Account: %s, Mail: %s") % (coreaccountid, serv_ref))
        # Check if a create was success
        if crid:
            logging.getLogger(_("Power Email")).info(_("Mail %s Saved successfully as ID: %s for Account: %s.") % (serv_ref, crid, coreaccountid))
            # logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("Mail %s Saved successfully as ID: %s for Account: %s.") % (serv_ref, crid, coreaccountid))
            # If there are attachments save them as well
            if parsed_mail['attachments']:
                self.save_attachments(cr, uid, mail, mailboxref, parsed_mail, coreaccountid, context)
            return True
        else:
            logging.getLogger(_("Power Email")).info(_("IMAP Mail -> Mailbox create error Account: %s, Mail: %s") % (coreaccountid, mail[0].split()[0]))
            # logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("IMAP Mail -> Mailbox create error Account: %s, Mail: %s") % (coreaccountid, mail[0].split()[0]))

    def save_attachments(self, cr, uid, mail, id, parsed_mail, coreaccountid, context=None):
        # logger = netsvc.Logger()
        att_obj = self.env('ir.attachment')
        mail_obj = self.env('poweremail.mailbox')
        att_ids = []
        for each in parsed_mail['attachments']:  # Get each attachment
            new_att_vals = {
                'name': self.decode_header_text(mail['subject']) + '(' + each[0] + ')',
                'datas': base64.b64encode(each[2] or ''),
                'datas_fname': each[1],
                'description': (self.decode_header_text(mail['subject']) or _('No Subject')) + " [Type:" + (each[0] or 'Unknown') + ", Filename:" + (
                        each[1] or 'No Name') + "]",
                'res_model': 'poweremail.mailbox',
                'res_id': id
            }
            att_ids.append(att_obj.create(cr, uid, new_att_vals, context))
            logging.getLogger(_("Power Email")).info(_("Downloaded & saved %s attachments Account: %s.") % (len(att_ids), coreaccountid))
            # logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("Downloaded & saved %s attachments Account: %s.") % (len(att_ids), coreaccountid))
            # Now attach the attachment ids to mail
            if mail_obj.write(cr, uid, id, {'pem_attachments_ids': [[6, 0, att_ids]]}, context):
                logging.getLogger(_("Power Email")).info(_("Attachment to mail for %s relation success! Account: %s.") % (id, coreaccountid))
                # logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("Attachment to mail for %s relation success! Account: %s.") % (id, coreaccountid))
            else:
                logging.getLogger(_("Power Email")).info(_("Attachment to mail for %s relation failed Account: %s.") % (id, coreaccountid))
                # logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Attachment to mail for %s relation failed Account: %s.") % (id, coreaccountid))

    def get_mails(self):
        print('======get_mails===0')
        context = self.env.context

        for rec in self:
            print('======get_mails===1', rec.iserver, rec.isport, rec.isuser, rec.ispass, rec.iserver_type)
            if rec.iserver and rec.isport and rec.isuser and rec.ispass:
                if rec.iserver_type == 'imap' and rec.isfolder:
                    # Try Connecting to Server
                    try:
                        if rec.isssl:
                            serv = imaplib.IMAP4_SSL(rec.iserver, rec.isport)
                        else:
                            serv = imaplib.IMAP4(rec.iserver, rec.isport)
                    except imaplib.IMAP4.error as error:
                        logging.getLogger(_("Power Email")).info(_("IMAP Server Error Account: %s Error: %s.") % (id, error))
                        # logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("IMAP Server Error Account: %s Error: %s.") % (id, error))
                    # Try logging in to server
                    try:
                        serv.login(rec.isuser, rec.ispass)
                    except imaplib.IMAP4.error as error:
                        logging.getLogger(_("Power Email")).info(_("IMAP Server Login Error Account: %s Error: %s.") % (id, error))
                        # logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("IMAP Server Login Error Account: %s Error: %s.") % (id, error))
                    logging.getLogger(_("Power Email")).info(_("IMAP Server Connected & logged in successfully Account: %s.") % (id))
                    # logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("IMAP Server Connected & logged in successfully Account: %s.") % (id))
                    # Select IMAP folder
                    try:
                        typ, msg_count = serv.select('"%s"' % rec.isfolder)
                    except imaplib.IMAP4.error as error:
                        logging.getLogger(_("Power Email")).info(_("IMAP Server Folder Selection Error Account: %s Error: %s.") % (id, error))
                        # logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("IMAP Server Folder Selection Error Account: %s Error: %s.") % (id, error))
                        raise Warning(_('Power Email'), _(
                            'IMAP Server Folder Selection Error Account: %s Error: %s.\nCheck account settings if you have selected a folder.') % (
                                          id, error))
                    logging.getLogger(_("Power Email")).info(_("IMAP Folder selected successfully Account:%s.") % (id))
                    # logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("IMAP Folder selected successfully Account:%s.") % (id))
                    logging.getLogger(_("Power Email")).info(_("IMAP Folder Statistics for Account: %s: %s") % (
                        id, serv.status('"%s"' % rec.isfolder, '(MESSAGES RECENT UIDNEXT UIDVALIDITY UNSEEN)')[1][0]))
                    # logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("IMAP Folder Statistics for Account: %s: %s") % (id, serv.status('"%s"' % rec.isfolder, '(MESSAGES RECENT UIDNEXT UIDVALIDITY UNSEEN)')[1][0]))
                    # If there are newer mails than the ones in mailbox
                    # print int(msg_count[0]),rec.last_mail_id
                    if rec.last_mail_id < int(msg_count[0]):
                        if rec.rec_headers_den_mail:
                            # Download Headers Only
                            for i in range(rec.last_mail_id + 1, int(msg_count[0]) + 1):
                                typ, msg = serv.fetch(str(i), '(FLAGS BODY.PEEK[HEADER])')
                                for mails in msg:
                                    if type(mails) == type(('tuple', 'type')):
                                        mail = email.message_from_string(mails[1])
                                        ctx = context.copy()
                                        if '\Seen' in mails[0]:
                                            ctx['state'] = 'read'
                                        if self.save_header(cr, uid, mail, id, mails[0].split()[0],
                                                            ctx):  # If saved succedfully then increment last mail recd
                                            self.write(cr, uid, id, {'last_mail_id': mails[0].split()[0]}, context)
                        else:  # Receive Full Mail first time itself
                            # Download Full RF822 Mails
                            for i in range(rec.last_mail_id + 1, int(msg_count[0]) + 1):
                                typ, msg = serv.fetch(str(i), '(FLAGS RFC822)')
                                for j in range(0, len(msg) / 2):
                                    mails = msg[j * 2]
                                    flags = msg[(j * 2) + 1]
                                    if type(mails) == type(('tuple', 'type')):
                                        ctx = context.copy()
                                        if '\Seen' in flags:
                                            ctx['state'] = 'read'
                                        mail = email.message_from_string(mails[1])
                                        if self.save_fullmail(cr, uid, mail, id, mails[0].split()[0],
                                                              ctx):  # If saved succedfully then increment last mail recd
                                            self.write(cr, uid, id, {'last_mail_id': mails[0].split()[0]}, context)
                    serv.close()
                    serv.logout()
                elif rec.iserver_type == 'pop3':
                    print('======get_mails===2')
                    try:
                        if rec.isssl:
                            serv = poplib.POP3_SSL(rec.iserver, rec.isport)
                        else:
                            serv = poplib.POP3(rec.iserver, rec.isport)
                    except Exception as error:
                        logging.getLogger(_("Power Email")).info(_("POP3 Server Error Account: %s Error: %s.") % (id, error))
                    try:
                        serv.user(rec.isuser)
                        serv.pass_(rec.ispass)
                    except Exception as error:
                        logging.getLogger(_("Power Email")).info(_("POP3 Server Login Error Account: %s Error: %s.") % (id, error))
                        # logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("POP3 Server Login Error Account: %s Error: %s.") % (id, error))


                    print('======get_mails===3', rec.last_mail_id, serv.stat()[0])
                    if rec.last_mail_id < serv.stat()[0]:
                        if rec.rec_headers_den_mail:
                            # Download Headers Only
                            for msgid in range(rec.last_mail_id + 1, serv.stat()[0] + 1):
                                resp, msg, octet = serv.top(msgid, 20)  # 20 Lines from the content
                                mail = email.message_from_string(string.join(msg, "\n"))
                                if self.save_header(cr, uid, mail, id, msgid):  # If saved succedfully then increment last mail recd
                                    self.write(cr, uid, id, {'last_mail_id': msgid}, context)
                        else:  # Receive Full Mail first time itself
                            # Download Full RF822 Mails
                            for msgid in range(rec.last_mail_id + 1, serv.stat()[0] + 1):
                                resp, msg, octet = serv.retr(msgid)  # Full Mail
                                print('===>', msgid, resp, msg, octet)
                                mail = email.message_from_bytes(msg[1])
                                print('==msg', mail)
                                if self.save_header(mail,  msgid):  # If saved succedfully then increment last mail recd
                                    self.last_mail_id = msgid
                else:
                    logging.getLogger(_("Power Email")).info(
                        _("Incoming server login attempt dropped Account: %s Check if Incoming server attributes are complete.") % (id))
                    # logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Incoming server login attempt dropped Account: %s Check if Incoming server attributes are complete.") % (id))

    def get_fullmail(self, cr, uid, mailid, context):
        # The function downloads the full mail for which only header was downloaded
        # ID:of poeremail core account
        # context: should have mailboxref, the ID of mailbox record
        server_ref = self.env(
            'poweremail.mailbox'
        ).read(cr, uid, mailid,
               ['server_ref'],
               context)['server_ref']
        id = self.env(
            'poweremail.mailbox'
        ).read(cr, uid, mailid,
               ['pem_account_id'],
               context)['pem_account_id'][0]
        # logger = netsvc.Logger()
        # The Main reception function starts here
        logging.getLogger(_("Power Email")).info(_("Starting Full mail reception for mail: %s.") % (id))
        # logger.notifyChannel(_("Power Email"),netsvc.LOG_INFO,_("Starting Full mail reception for mail: %s.") % (id))
        rec = self.browse(cr, uid, id, context)
        if rec:
            if rec.iserver and rec.isport and rec.isuser and rec.ispass:
                if rec.iserver_type == 'imap' and rec.isfolder:
                    # Try Connecting to Server
                    try:
                        if rec.isssl:
                            serv = imaplib.IMAP4_SSL(
                                rec.iserver,
                                rec.isport
                            )
                        else:
                            serv = imaplib.IMAP4(
                                rec.iserver,
                                rec.isport
                            )
                    except imaplib.IMAP4.error as error:
                        logging.getLogger(_("Power Email")).info(_("IMAP Server Error Account: %s Error: %s.") % (id, error))
                        # logger.notifyChannel(_("Power Email"),netsvc.LOG_ERROR,_("IMAP Server Error Account: %s Error: %s.") % (id, error))
                    # Try logging in to server
                    try:
                        serv.login(rec.isuser, rec.ispass)
                    except imaplib.IMAP4.error as error:
                        logging.getLogger(_("Power Email")).info(_("IMAP Server Login Error Account:%s Error: %s.") % (id, error))
                        # logger.notifyChannel(_("Power Email"),netsvc.LOG_ERROR,_("IMAP Server Login Error Account:%s Error: %s.") % (id, error))
                    logging.getLogger(_("Power Email")).info(_("IMAP Server Connected & logged in successfully Account: %s.") % (id))
                    # logger.notifyChannel(_("Power Email"),netsvc.LOG_INFO,_("IMAP Server Connected & logged in successfully Account: %s.") % (id))
                    # Select IMAP folder
                    try:
                        typ, msg_count = serv.select('"%s"' % rec.isfolder)  # typ,msg_count: practically not used here
                    except imaplib.IMAP4.error as error:
                        logging.getLogger(_("Power Email")).info(_("IMAP Server Folder Selection Error. Account: %s Error: %s.") % (id, error))
                        # logger.notifyChannel(_("Power Email"),netsvc.LOG_ERROR,_("IMAP Server Folder Selection Error. Account: %s Error: %s.") % (id, error))
                    logging.getLogger(_("Power Email")).info(_("IMAP Folder selected successfully Account: %s.") % (id))
                    # logger.notifyChannel(_("Power Email"),netsvc.LOG_INFO,_("IMAP Folder selected successfully Account: %s.") % (id))
                    logging.getLogger(_("Power Email")).info(_("IMAP Folder Statistics for Account: %s: %s") % (
                        id, serv.status('"%s"' % rec.isfolder, '(MESSAGES RECENT UIDNEXT UIDVALIDITY UNSEEN)')[1][0]))
                    # logger.notifyChannel(_("Power Email"),netsvc.LOG_INFO,_("IMAP Folder Statistics for Account: %s: %s") % (id,serv.status('"%s"' % rec.isfolder,'(MESSAGES RECENT UIDNEXT UIDVALIDITY UNSEEN)')[1][0]))
                    # If there are newer mails than the ones in mailbox
                    typ, msg = serv.fetch(str(server_ref), '(FLAGS RFC822)')
                    for i in range(0, len(msg) / 2):
                        mails = msg[i * 2]
                        flags = msg[(i * 2) + 1]
                        if type(mails) == type(('tuple', 'type')):
                            if '\Seen' in flags:
                                context['state'] = 'read'
                            mail = email.message_from_string(mails[1])
                            self.complete_mail(cr, uid, mail, id,
                                               server_ref, mailid, context)
                    serv.close()
                    serv.logout()
                elif rec.iserver_type == 'pop3':
                    # Try Connecting to Server
                    try:
                        if rec.isssl:
                            serv = poplib.POP3_SSL(
                                rec.iserver,
                                rec.isport
                            )
                        else:
                            serv = poplib.POP3(
                                rec.iserver,
                                rec.isport
                            )
                    except Exception as error:
                        logging.getLogger(_("Power Email")).info(_("POP3 Server Error Account: %s Error: %s.") % (id, error))
                        # logger.notifyChannel(_("Power Email"),netsvc.LOG_ERROR,_("POP3 Server Error Account: %s Error: %s.") % (id, error))
                    # Try logging in to server
                    try:
                        serv.user(rec.isuser)
                        serv.pass_(rec.ispass)
                    except Exception as error:
                        logging.getLogger(_("Power Email")).info(_("POP3 Server Login Error Account: %s Error: %s.") % (id, error))
                        # logger.notifyChannel(_("Power Email"),netsvc.LOG_ERROR,_("POP3 Server Login Error Account: %s Error: %s.") % (id, error))
                    logging.getLogger(_("Power Email")).info(_("POP3 Server Connected & logged in successfully Account: %s.") % (id))
                    # logger.notifyChannel(_("Power Email"),netsvc.LOG_INFO,_("POP3 Server Connected & logged in successfully Account: %s.") % (id))
                    logging.getLogger(_("Power Email")).info(
                        _("POP3 Statistics: %s mails of %s size for Account: %s:") % (serv.stat()[0], serv.stat()[1], id))
                    # logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("POP3 Statistics: %s mails of %s size for Account: %s:") % (serv.stat()[0], serv.stat()[1], id))
                    # Download Full RF822 Mails
                    resp, msg, octet = serv.retr(server_ref)  # Full Mail
                    mail = email.message_from_string(string.join(msg, "\n"))
                    self.complete_mail(cr, uid, mail, id,
                                       server_ref, mailid, context)
                else:
                    logging.getLogger(_("Power Email")).info(
                        _("Incoming server login attempt dropped Account: %s\nCheck if Incoming server attributes are complete.") % (id))
                    # logger.notifyChannel(_("Power Email"),netsvc.LOG_ERROR,_("Incoming server login attempt dropped Account: %s\nCheck if Incoming server attributes are complete.") % (id))

    def receive_email(self):
        self.get_mails()
        return True

    def send_emial(self):
        self.env['poweremail.mailbox'].send_all_mail()
        return True

    def get_payloads(self, mail):
        """
        """
        # This function will go through the mail and identify the payloads and return them
        parsed_mail = {
            'text': False,
            'html': False,
            'attachments': []
        }
        for part in mail.walk():
            mail_part_type = part.get_content_type()
            if mail_part_type == 'text/plain':
                parsed_mail['text'] = tools.ustr(part.get_payload(decode=True))  # decode=True to decode a MIME message
            elif mail_part_type == 'text/html':
                parsed_mail['html'] = tools.ustr(part.get_payload(decode=True))  # Is decode=True needed in html MIME messages?
            elif not mail_part_type.startswith('multipart'):
                parsed_mail['attachments'].append((mail_part_type, part.get_filename(), part.get_payload(decode=True)))
        return parsed_mail

    def decode_header_text(self, text):
        """ Decode internationalized headers RFC2822.
            To, CC, BCC, Subject fields can contain
            text slices with different encodes, like:
                =?iso-8859-1?Q?Enric_Mart=ED?= <enricmarti@company.com>,
                =?Windows-1252?Q?David_G=F3mez?= <david@company.com>
            Sometimes they include extra " character at the beginning/
            end of the contact name, like:
                "=?iso-8859-1?Q?Enric_Mart=ED?=" <enricmarti@company.com>
            and decode_header() does not work well, so we use regular
            expressions (?=   ? ?   ?=) to split the text slices
        """
        if not text:
            return text
        p = re.compile("(=\?.*?\?.\?.*?\?=)")
        text2 = ''
        try:
            for t2 in p.split(text):
                text2 += ''.join(
                    [s.decode(
                        t or 'ascii'
                    ) for (s, t) in decode_header(t2)]
                ).encode('utf-8')
        except:
            return text
        return text2


class PoweremailSelectFolder(models.Model):
    _name = "poweremail.core_selfolder"
    _description = "Shows a list of IMAP folders"

    def makereadable(self, imap_folder):
        if imap_folder:
            # We consider imap_folder may be in one of the following formats:
            # A string like this: '(\HasChildren) "/" "INBOX"'
            # Or a tuple like this: ('(\\HasNoChildren) "/" {18}', 'INBOX/contacts')
            if isinstance(imap_folder, tuple):
                return imap_folder[1]
            result = re.search(
                r'(?:\([^\)]*\)\s\")(.)(?:\"\s)(?:\")?([^\"]*)(?:\")?',
                imap_folder)
            seperator = result.groups()[0]
            folder_readable_name = ""
            splitname = result.groups()[1].split(seperator)  # Not readable now
            # If a parent and child exists, format it as parent/child/grandchild
            if len(splitname) > 1:
                for i in range(0, len(splitname) - 1):
                    folder_readable_name = splitname[i] + '/'
                folder_readable_name = folder_readable_name + splitname[-1]
            else:
                folder_readable_name = result.groups()[1].split(seperator)[0]
            return folder_readable_name
        return False

    def _get_folders(self):
        account_id = self.env.context.get('account_id')
        if account_id:
            record = self.env['poweremail.core_accounts'].browse(account_id)
            if record:
                folderlist = []
                try:
                    if record.isssl:
                        serv = IMAPClient(record.iserver, use_uid=True, ssl=True)
                    else:
                        serv = IMAPClient(record.iserver, use_uid=True, ssl=False)
                except imaplib.IMAP4.error as error:
                    raise Warning(_("IMAP Server Error"),
                                  _("An error occurred: %s") % error)
                except Exception as error:
                    raise Warning(_("IMAP Server connection Error"),
                                  _("An error occurred: %s") % error)
                try:
                    serv.login(record.isuser, record.ispass)
                except imaplib.IMAP4.error as error:
                    raise Warning(_("IMAP Server Login Error"),
                                  _("An error occurred: %s") % error)
                except Exception as error:
                    raise Warning(_("IMAP Server Login Error"),
                                  _("An error occurred: %s") % error)
                try:
                    for folders in serv.list_folders()[1:]:
                        print('==folders=', folders)
                        folder_readable_name = folders[2]
                        print('==folders=', folder_readable_name)
                        if isinstance(folders, tuple):
                            data = folders[0] + folders[1]
                        else:
                            data = folders
                        if data.find('Noselect') == -1:  # If it is a selectable folder
                            if folder_readable_name:
                                folderlist.append(
                                    (folder_readable_name,
                                     folder_readable_name)
                                )
                        if folder_readable_name == 'INBOX':
                            self.inboxvalue = folder_readable_name

                except Exception as error:
                    raise Warning(_("IMAP Server Folder Error An error occurred: %s") % error)
            else:
                folderlist = [('invalid', 'Invalid')]
        else:
            folderlist = [('invalid', 'Invalid')]
        return folderlist

    name = fields.Many2one('poweremail.core_accounts', 'Email Account', readonly=True, default=lambda self: self.env.context.get('account_id'))
    folder = fields.Selection(_get_folders, string="IMAP Folder")

    def sel_folder(self):
        """
        TODO: Doc This
        """
        account = self.env['poweremail.core_accounts'].browse(self.env.context.get('account_id'))
        if self.folder:
            if not self.folder == 'invalid':
                account.write({'isfolder': self.folder})
                return {'type': 'ir.actions.act_window_close'}
            else:
                raise Warning(_("Folder Error"), _("This is an invalid folder"))
        else:
            raise Warning(_("Folder Error"), _("Select a folder before you save record"))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
