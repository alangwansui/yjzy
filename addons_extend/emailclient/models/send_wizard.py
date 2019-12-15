# -*- coding: utf-8 -*-

import base64
import time

import logging
from odoo import models, fields, api, _, tools



class poweremail_send_wizard(models.TransientModel):
    _name = 'poweremail.send.wizard'
    _description = 'This is the wizard for sending mail'
    _rec_name = "subject"

    state=fields.Selection([
                        ('single','Simple Mail Wizard Step 1'),
                        ('multi','Multiple Mail Wizard Step 1'),
                        ('send_type','Send Type'),
                        ('done','Wizard Complete')],'Status',readonly=True)
    ref_template=fields.Many2one('poweremail.templates','Template',readonly=True)
    rel_model=fields.Many2one('ir.model','Model',readonly=True)
    rel_model_ref=fields.Integer('Referred Document',readonly=True)
    ffrom = fields.Selection([(1,1),(2,2)],'From Account',select=True)
    to=fields.Char('To',size=250,required=True)
    cc=fields.Char('CC',size=250,)
    bcc=fields.Char('BCC',size=250,)
    subject=fields.Char('Subject',size=200)
    body_text=fields.Text('Body',)
    body_html=fields.Text('Body',)
    report=fields.Char('Report File Name',size=100,)
    signature=fields.Boolean('Attach my signature to mail')
        #'filename=fields.Text('File Name'),
    requested=fields.Integer('No of requested Mails',readonly=True)
    generated=fields.Integer('No of generated Mails',readonly=True)
    full_success=fields.Boolean('Complete Success',readonly=True)
    attachment_ids= fields.Many2many('ir.attachment','send_wizard_attachment_rel', 'wizard_id', 'attachment_id', 'Attachments')
    single_email= fields.Boolean("Single email")





    def sav_to_drafts(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mailid = self.save_to_mailbox(cr, uid, ids, context)
        if self.env('poweremail.mailbox').write(cr, uid, mailid, {'folder':'drafts'}, context):
            return {'type':'ir.actions.act_window_close' }

    def send_mail(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mailid = self.save_to_mailbox(cr, uid, ids, context)
        if self.env('poweremail.mailbox').write(cr, uid, mailid, {'folder':'outbox'}, context):
            return {'type':'ir.actions.act_window_close' }

    def get_generated(self, cr, uid, ids=None, context=None):
        if ids is None:
            ids = []
        if context is None:
            context = {}
        #logger = netsvc.Logger()
        if context['src_rec_ids'] and len(context['src_rec_ids'])>1:
            #Means there are multiple items selected for email.
            mail_ids = self.save_to_mailbox(cr, uid, ids, context)
            if mail_ids:
                self.env('poweremail.mailbox').write(cr, uid, mail_ids, {'folder':'outbox'}, context)
                #logger.notifyChannel(_("Power Email"), netsvc.LOG_INFO, _("Emails for multiple items saved in outbox."))
                logging.getLogger(_("Power Email")).info(_("Emails for multiple items saved in outbox."))
                self.write(cr, uid, ids, {
                    'generated':len(mail_ids),
                    'state':'done'
                }, context)
            else:
                raise Warning(_("Power Email"),_("Email sending failed for one or more objects."))
        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
