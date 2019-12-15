# -*- coding: utf-8 -*-

from odoo import api, fields, models
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class MessageTag(models.Model):
    _name = "message.tag"

    name = fields.Char(string='Tag Name')


class MessageFolder(models.Model):
    _name = "message.folder"

    name = fields.Char(string='Folder Name')


class Message(models.Model):
    _inherit = 'mail.message'

    # gmail = fields.Boolean('Gmail Message')
    msg_unread = fields.Boolean('Message Read')
    message_label = fields.Selection([('inbox','Inbox'), ('starred', 'Starred'),('done', 'Done'), ('snoozed', 'Snoozed'), ('draft', 'Draft'), ('sent', 'SENT'), ('trace', 'TRACE')], string='Message Label', default="inbox")
    draft_message_id = fields.Char(string='Draft Message ID')
    snoozed_time = fields.Datetime('Snoozed Time')
    partner_followers = fields.Many2many('res.partner', 'mail_message_partner_rel', 'mail_id', 'partner_id', string='Partners')
    tag_ids = fields.Many2many('message.tag', 'mail_message_tags_rel', 'mail_id', 'tag_id', string='Tag')
    folder_id = fields.Many2one('message.folder', string='Folder')

    # @api.model
    # def create(self, values):
    #     rec = super(Message, self).create(values)
    #     tasks = self.env['project.task'].search([('id', '=', rec.res_id)])
    #     if tasks:
    #         partners = tasks.message_follower_ids.mapped('partner_id.id')
    #         rec.partner_followers = [(6, 0, partners)]
    #     return rec

    def get_messages_time(self, your_time=None):
        if your_time == 'tomorrow':
            snooze = fields.Datetime.context_timestamp(self, datetime.now() + timedelta(days=1)).strftime("%a %I:%M %p")
        else:
            snooze = fields.Datetime.context_timestamp(self, datetime.now() + timedelta(hours=2)).strftime("%I:%M %p")
        return snooze

    # @api.model
    # def set_to_inbox(self):
    #     domain = [('message_label', '=', 'snoozed')]
    #     all_message = self.sudo().search(domain)
    #     for msg in all_message:
    #         now = fields.Datetime.context_timestamp(self , fields.Datetime.from_string(fields.Datetime.now()))
    #         snoozed_time = fields.Datetime.context_timestamp(self, fields.Datetime.from_string(msg.snoozed_time))
    #         if now >= snoozed_time:
    #             msg.message_label = 'inbox'
    #     return

