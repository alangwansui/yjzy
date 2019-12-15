# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import imaplib
import smtplib
import poplib
from odoo.exceptions import UserError, Warning


class personal_email_credentials(models.Model):

    _name = 'personal.email.credentials'

    _default_smtp_server_port = 465

    user_id = fields.Many2one('res.users', 'User Id')
    email_address = fields.Char('User Email Address')
    password = fields.Char('Password')
    imap_server = fields.Char('IMAP Server')
    imap_port = fields.Char('IMAP Port', default=993)

    smtp_server = fields.Char('SMTP Server')
    smtp_port = fields.Char('SMTP Port', default=465)

    pop_server = fields.Char('POP Server')
    pop_port = fields.Char('POP Port', default=995)

    default = fields.Boolean('Default')

    def login_check(self):
        self.ensure_one()

        msg = ''

        # 连接smtp服务器。
        email_client = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
        try:
            # 验证邮箱及密码是否正确
            email_client.login(self.email_address, self.password)
            msg += "smtp 登录OK  "
        except:
            raise Warning("smtp----sorry, username or password not correct or another problem occur")
        finally:
            # 关闭连接
            email_client.close()


        #验证POP
        try:
            # 连接pop服务器。如果没有使用SSL，将POP3_SSL()改成POP3()即可其他都不需要做改动
            email_server = poplib.POP3_SSL(host=self.pop_server, port=self.pop_port, timeout=10)
        except:
            raise Warning("pop3----sorry the given email server address connect time out")
        try:
            # 验证邮箱是否存在
            email_server.user(self.email_address)
        except:
            raise Warning("pop3----sorry the given email address seem do not exist")
        try:
            # 验证邮箱密码是否正确
            email_server.pass_(self.password)
            msg += 'POP 登录OK '
        except:
            raise  Warning("pop3----sorry the given username seem do not correct")


        #验证IMAP
        try:
            # 连接imap服务器。如果没有使用SSL，将 IMAP4_SSL() 改成IMAP4()即可其他都不需要做改动
            email_server = imaplib.IMAP4_SSL(host=self.imap_server, port=self.imap_port)
        except:
            raise Warning("imap4----sorry the given email server address connect time out")
        try:
            # 验证邮箱及密码是否正确
            email_server.login(self.email_address, self.password)
            msg += 'IMAP 登录OK '
        except:
            raise  Warning("imap4----sorry the given email address or password seem do not correct")


        raise Warning(msg)

    @api.model
    def create__(self, vals):
        if vals.get('default') and self.search([('user_id', '=', vals.get('user_id')), ('default', '=', vals.get('default'))]):
            raise UserError(_('You can only select one default account.'))
        # try:
        #     mail = imaplib.SMTP_SSL(vals.get('imap_server'), 465)
        #
        # except:
        #     raise UserError(_('IMAP Server not found.'))
        try:
            connection = smtplib.SMTP_SSL(vals.get('smtp_server'), '465')
        except:
            raise UserError(_('SMTP Server not found.'))
        try:
            print('===', vals.get('email_address'), vals.get('password'))
            connection.login(vals.get('email_address'), vals.get('password'))
        except:
            raise UserError(_('SMTP Login Failed for %s.') % vals.get('email_address'))
        try:
            mail.login(vals.get('email_address'), vals.get('password'), 465)
        except:
            raise UserError(_('IMAP Login Failed for %s.') % vals.get('email_address'))
            # raise UserError(_('Login Failed.'))
        return super(personal_email_credentials, self).create(vals)

    @api.multi
    def write__(self, vals):
        if vals.get('default') and self.search([('user_id', '=', self.user_id.id), ('default', '=', vals.get('default'))]):
            raise UserError(_('You can only select one default account.'))
        mail = imaplib.IMAP4_SSL(self.imap_server)
        connection = smtplib.SMTP_SSL(self.smtp_server, '465')
        if vals.get('imap_server'):
            try:
                mail = imaplib.IMAP4_SSL(vals.get('imap_server'))
            except:
                raise UserError(_('IMAP Server not found.'))
        if vals.get('smtp_server'):
            try:
                connection = smtplib.SMTP_SSL(vals.get('smtp_server'), '465')
            except:
                raise UserError(_('SMTP Server not found.'))

        if vals.get('email_address') or vals.get('password'):
            if vals.get('email_address') and vals.get('password'):
                try:
                    mail.login(vals.get('email_address'), vals.get('password'))
                except:
                    raise UserError(_('IMAP Login Failed for %s.') % vals.get('email_address'))
                try:
                    connection.login(vals.get('email_address'), vals.get('password'))
                except:
                    raise UserError(_('SMTP Login Failed for %s.') % vals.get('email_address'))

            if vals.get('email_address') and not vals.get('password'):
                try:
                    mail.login(vals.get('email_address'), self.password)
                except:
                    raise UserError(_('IMAP Login Failed for %s.')%vals.get('email_address'))
                try:
                    connection.login(vals.get('email_address'), self.password)
                except:
                    raise UserError(_('SMTP Login Failed for %s.') % vals.get('email_address'))

            if vals.get('password')and not vals.get('email_address'):
                try:
                    mail.login(self.email_address, vals.get('password'))
                except:
                    raise UserError(_('IMAP Login Failed for %s.') % self.email_address)
                try:
                    connection.login(self.email_address, vals.get('password'))
                except:
                    raise UserError(_('SMTP Login Failed for %s.') % self.email_address)
        return super(personal_email_credentials, self).write(vals)

class res_users(models.Model):

    _inherit = 'res.users'

    personal_email_credentials_ids = fields.One2many('personal.email.credentials', 'user_id', 'Personal Email Credentials')
