# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
import time
import logging


# LOGGER = netsvc.Logger()

class PoweremailMailbox(models.Model):
    _name = "poweremail.mailbox"
    _description = 'Power Email Mailbox included all type inbox,outbox,junk..'
    _rec_name = "pem_subject"
    _order = "date_mail desc"

    def run_mail_scheduler(self, cursor, user, context=None):
        """
        This method is called by Open ERP Scheduler
        to periodically receive & fetch mails
        """
        try:
            self.get_all_mail(cursor, user, context={'all_accounts': True})
        except Exception as e:
            logging.getLogger(_("Power Email")).info(_("Error receiving mail: %s") % str(e))
            # LOGGER.notifyChannel(_("Power Email"),netsvc.LOG_ERROR,_("Error receiving mail: %s") % str(e))
        try:
            self.send_all_mail(cursor, user, context)
        except Exception as e:
            logging.getLogger(_("Power Email")).info(_("Error sending mail: %s") % str(e))
            # LOGGER.notifyChannel(_("Power Email"),netsvc.LOG_ERROR,_("Error sending mail: %s") % str(e))

    def get_all_mail(self, cr, uid, context=None):
        if context is None:
            context = {}
        # 8888888888888 FETCHES MAILS 8888888888888888888#
        # email_account: THe ID of poweremil core account
        # Context should also have the last downloaded mail for an account
        # Normlly this function is expected to trigger from scheduler hence the value will not be there
        core_obj = self.env('poweremail.core_accounts')
        if not 'all_accounts' in list(context.keys()):
            # Get mails from that ID only
            core_obj.get_mails(cr, uid, [context['email_account']])
        else:
            accounts = core_obj.search(cr, uid, [('state', '=', 'approved')], context=context)
            core_obj.get_mails(cr, uid, accounts)

    def get_fullmail(self, cr, uid, context=None):
        if context is None:
            context = {}
        # 8888888888888 FETCHES MAILS 8888888888888888888#
        core_obj = self.env('poweremail.core_accounts')
        if 'mailboxref' in list(context.keys()):
            # Get mails from that ID only
            core_obj.get_fullmail(cr, uid, context['email_account'], context)
        else:
            raise Warning(_("Mail fetch exception"), _("No information on which mail should be fetched fully"))

    def send_all_mail(self, cr, uid, ids=None, context=None):
        if ids is None:
            ids = []
        if context is None:
            context = {}
        # 8888888888888 SENDS MAILS IN OUTBOX 8888888888888888888#
        # get ids of mails in outbox
        filters = [('folder', '=', 'outbox'), ('state', '!=', 'sending')]
        if 'filters' in list(context.keys()):
            for each_filter in context['filters']:
                filters.append(each_filter)
        ids = self.search(cr, uid, filters, context=context)
        # To prevent resend the same emails in several send_all_mail() calls
        self.write(cr, uid, ids, {'state': 'sending'}, context)
        # send mails one by one
        self.send_this_mail(cr, uid, ids, context)
        return True

    def send_this_mail(self, cr, uid, ids=None, context=None):
        if ids is None:
            ids = []
        # 8888888888888 SENDS THIS MAIL IN OUTBOX 8888888888888888888#
        # send mails one by one
        for id in ids:
            try:
                core_obj = self.env('poweremail.core_accounts')
                values = self.read(cr, uid, id, [], context)  # Values will be a dictionary of all entries in the record ref by id
                pem_to = (values['pem_to'] or '').strip()
                if pem_to in ('', 'False'):
                    continue
                payload = {}
                if values['pem_attachments_ids']:
                    # Get filenames & binary of attachments
                    for attid in values['pem_attachments_ids']:
                        attachment = self.env('ir.attachment').browse(cr, uid, attid, context)  # ,['datas_fname','datas'])
                        att_name = attachment.datas_fname or attachment.name
                        counter = 1
                        while att_name in payload:
                            att_name = "%s%d" % (attachment.datas_fname or attachment.name, counter)
                            counter += 1
                        payload[att_name] = attachment.datas
                result = core_obj.send_mail(cr, uid,
                                            [values['pem_account_id'][0]],
                                            {'To': values.get('pem_to', '') or '', 'CC': values.get('pem_cc', '') or '',
                                             'BCC': values.get('pem_bcc', '') or ''},
                                            values['pem_subject'] or '',
                                            {'text': values.get('pem_body_text', '') or '', 'html': values.get('pem_body_html', '') or ''},
                                            payload=payload, context=context)
                if result == True:
                    self.write(cr, uid, id, {'folder': 'sent', 'state': 'na', 'date_mail': time.strftime("%Y-%m-%d %H:%M:%S")}, context)
                    self.historise(cr, uid, [id], "Email sent successfully", context)
                else:
                    self.historise(cr, uid, [id], result, context)
            except Exception as error:
                # logger = netsvc.Logger()
                logging.getLogger(_("Power Email")).info(
                    _("Sending of Mail %s failed. Probable Reason: Could not login to server\nError: %s") % (id, error))
                # logger.notifyChannel(_("Power Email"), netsvc.LOG_ERROR, _("Sending of Mail %s failed. Probable Reason: Could not login to server\nError: %s") % (id, error))
                self.historise(cr, uid, [id], error, context)
            self.write(cr, uid, id, {'state': 'na'}, context)
        return True

    def historise(self, cr, uid, ids, message='', context=None):
        for id in ids:
            history = self.read(cr, uid, id, ['history'], context).get('history', '')
            self.write(cr, uid, id, {'history': history or '' + "\n" + time.strftime("%Y-%m-%d %H:%M:%S") + ": " + tools.ustr(message)}, context)

    def complete_mail(self, cr, uid, ids, context=None):
        # 8888888888888 COMPLETE PARTIALLY DOWNLOADED MAILS 8888888888888888888#
        # FUNCTION get_fullmail(self,cr,uid,mailid) in core is used where mailid=id of current email,
        for id in ids:
            self.env('poweremail.core_accounts').get_fullmail(cr, uid, id, context)
            self.historise(cr, uid, [id], "Full email downloaded", context)

    pem_from = fields.Char('From', size=64)
    pem_to = fields.Char('Recepient (To)',size=250, )
    pem_cc = fields.Char(' CC', size=250)
    pem_bcc = fields.Char( ' BCC', size=250)
    pem_subject = fields.Char(  ' Subject',   size=200, )
    pem_body_text = fields.Text(  'Standard Body (Text)')
    pem_body_html = fields.Text(  'Body (Text-Web Client Only)')
    pem_attachments_ids = fields.Many2many( 'ir.attachment','mail_attachments_rel', 'mail_id','att_id', 'Attachments')
    pem_account_id = fields.Many2one('poweremail.core_accounts', 'User account', required=True)
    pem_user = fields.Many2one('res.users', related='pem_account_id.user', string="User")
    server_ref = fields.Integer( 'Server Reference of mail',help="Applicable for inward items only.")
    pem_recd = fields.Char('Received at', size=50)
    mail_type = fields.Selection([
        ('multipart/mixed',
         'Has Attachments'),
        ('multipart/alternative',
         'Plain Text & HTML with no attachments'),
        ('multipart/related',
         'Intermixed content'),
        ('text/plain',
         'Plain Text'),
        ('text/html',
         'HTML Body'),
    ], 'Mail Contents')
    # I like GMAIL which allows putting same mail in many folders
    # Lets plan it for 0.9
    folder = fields.Selection([
        ('inbox', 'Inbox'),
        ('drafts', 'Drafts'),
        ('outbox', 'Outbox'),
        ('trash', 'Trash'),
        ('followup', 'Follow Up'),
        ('sent', 'Sent Items'),
    ], 'Folder', required=True)
    state = fields.Selection([
        ('read', 'Read'),
        ('unread', 'Un-Read'),
        ('na', 'Not Applicable'),
        ('sending', 'Sending'),
    ], 'Status', required=True)
    date_mail = fields.Datetime(
        'Rec/Sent Date')
    history = fields.Text(
        'History',
        readonly=True,
        store=True)

    _defaults = {
        'state': lambda *a: 'na',
        'folder': lambda *a: 'outbox',
    }

    def search__(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        if context.get('company', False):
            users_groups = self.env('res.users').browse(cr, uid, uid, context).groups_id
            group_acc_rel = {}
            # get all accounts and get a table of {group1:[account1,account2],group2:[account1]}
            for each_account_id in self.env('poweremail.core_accounts').search(cr, uid, [('state', '=', 'approved'), ('company', '=', 'yes')],
                                                                               context=context):
                account = self.env('poweremail.core_accounts').browse(cr, uid, each_account_id, context)
                for each_group in account.allowed_groups:
                    if not account.id in group_acc_rel.get(each_group, []):
                        groups = group_acc_rel.get(each_group, [])
                        groups.append(account.id)
                        group_acc_rel[each_group] = groups
            users_company_accounts = []
            for each_group in list(group_acc_rel.keys()):
                if each_group in users_groups:
                    for each_account in group_acc_rel[each_group]:
                        if not each_account in users_company_accounts:
                            users_company_accounts.append(each_account)
            args.append(('pem_account_id', 'in', users_company_accounts))
        return super(models.Model, self).search(cr, uid, args, offset, limit,
                                                order, context=context, count=count)


class PoweremailConversation(models.Model):
    """
    This is an ambitious approach to grouping emails
    by automatically grouping attributes
    Something like Gmail
    
    Warning: Incomplete
    """
    _name = "poweremail.conversation"
    _description = "Conversations are groups of related emails"

    name = fields.Char('Name', size=250)
    mails = fields.One2many('poweremail.mailbox',
                            'conversation_id',
                            'Related Emails')


class PoweremailMailboxConversation(models.Model):
    _inherit = "poweremail.mailbox"

    conversation_id = fields.Many2one('poweremail.conversation', 'Conversation')


PoweremailMailboxConversation()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
