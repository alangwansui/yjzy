from odoo import _, api, exceptions, fields, models, tools, SUPERUSER_ID


class mail_read_log(models.Model):
    _name = "mail.read.log"
    _rec_name = 'ip_address'
    _description = '邮件客户读取记录'

    mail_id = fields.Many2one('mail.mail', '邮件')
    ip_address = fields.Char('IP地址')


