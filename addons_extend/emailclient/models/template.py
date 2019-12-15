# -*- coding: utf-8 -*-
#########################################################################

import base64
import random
import time
import types
import logging

TEMPLATE_ENGINES = []

from odoo import models, fields, api, _
from odoo.tools import safe_eval
#Try and check the available templating engines
from mako.template import Template  #For backward combatibility
from mako.template import Template as MakoTemplate
from mako import exceptions
TEMPLATE_ENGINES.append(('mako', 'Mako Templates'))





def send_on_create(self, vals):
    one = self.old_create(vals)
    templates = self.env['poweremail.templates'].browse(self.template_ids)
    for template in templates:
        # Ensure it's still configured to send on create
        if template.send_on_create:
            self.env['poweremail.templates'].generate_mail(one)
    return one

def send_on_write(self, vals):
    one = self.old_write(vals)
    templates = self.env['poweremail.templates'].browse(self.template_ids)
    for template in templates:
        # Ensure it's still configured to send on write
        if template.send_on_write:
            template.generate_mail(one)
    return one




class poweremail_templates(models.Model):

    _name = "poweremail.templates"
    _description = 'Power Email Templates for Models'

    def change_model(self, cursor, user, ids, object_name, context=None):
        if object_name:
            mod_name = self.env('ir.model').read(
                                              cursor,
                                              user,
                                              object_name,
                                              ['model'], context)['model']
        else:
            mod_name = False
        return {
                'value':{'model_int_name':mod_name}
                }


    name = fields.Char('Name of Template', size=100, required=True)
    object_name= fields.Many2one('ir.model', 'Model')
    model_int_name=fields.Char('Model Internal Name', size=200,)
    def_to=fields.Char(
                'Recepient (To)',
                size=250,
                help="The default recepient of email. "
                "Placeholders can be used here.")
    def_cc=fields.Char(
                'Default CC',
                size=250,
                help="The default CC for the email. "
                "Placeholders can be used here.")
    def_bcc=fields.Char(
                'Default BCC',
                size=250,
                help="The default BCC for the email. "
                "Placeholders can be used here.")
    lang=fields.Char(
                'Language',
                size=250,
                help="The default language for the email. "
                "Placeholders can be used here. "
                "eg. ${object.partner_id.lang}")
    def_subject=fields.Char(
                'Default Subject',
                size=200,
                help="The default subject of email. "
                "Placeholders can be used here.",
                translate=True)
    def_body_text=fields.Text(
                'Standard Body (Text)',
                help="The text version of the mail.",
                translate=True)
    def_body_html=fields.Text(
                'Body (Text-Web Client Only)',
                help="The text version of the mail.",
                translate=True)
    use_sign=fields.Boolean(
                'Use Signature',
                help="The signature from the User details "
                "will be appened to the mail.")
    file_name=fields.Char(
                'File Name Pattern',
                size=200,
                help="File name pattern can be specified with placeholders. "
                "eg. 2009_SO003.pdf",
                translate=True)
    report_template=fields.Many2one(
                'ir.actions.report.xml',
                'Report to send')
        #'report_template=fields.reference('Report to send',[('ir.actions.report.xml','Reports')],size=128),
    allowed_groups=fields.Many2many(
                'res.groups',
                'template_group_rel',
                'templ_id', 'group_id',
                string="Allowed User Groups",
                help="Only users from these groups will be "
                "allowed to send mails from this Template.")
    enforce_from_account=fields.Many2one(
                'poweremail.core_accounts',
                string="Enforce From Account",
                help="Emails will be sent only from this account.",
                domain="[('company','=','yes')]")
    auto_email=fields.Boolean('Auto Email',
                help="Selecting Auto Email will create a server "
                "action for you which automatically sends mail after a "
                "new record is created.\nNote: Auto email can be enabled "
                "only after saving template.")
    save_to_drafts=fields.Boolean('Save to Drafts',
                    help="When automatically sending emails generated from"
                    " this template, save them into the Drafts folder rather"
                    " than sending them immediately.")
        #Referred Stuff - Dont delete even if template is deleted
    attached_wkf=fields.Many2one(
                'workflow',
                'Workflow')
    attached_activity=fields.Many2one(
                'workflow.activity',
                'Activity')
        #Referred Stuff - Delete these if template are deleted or they will crash the system
    server_action=fields.Many2one(
                'ir.actions.server',
                'Related Server Action',
                help="Corresponding server action is here.")
    ref_ir_act_window=fields.Many2one(
                'ir.actions.act_window',
                'Window Action',
                readonly=True)
    ref_ir_value=fields.Many2one(
                'ir.values',
                'Wizard Button',
               readonly=True)
        #Expression Builder fields
        #Simple Fields
    model_object_field=fields.Many2one(
                'ir.model.fields',
                string="Field",
                help="Select the field from the model you want to use."
                "\nIf it is a relationship field you will be able to "
                "choose the nested values in the box below.\n(Note: If "
                "there are no values make sure you have selected the "
                "correct model).",
                store=False)
    sub_object=fields.Many2one(
                'ir.model',
                'Sub-model',
                help='When a relation field is used this field '
                'will show you the type of field you have selected.',
                store=False)
    sub_model_object_field=fields.Many2one(
                'ir.model.fields',
                'Sub Field',
                help="When you choose relationship fields "
                "this field will specify the sub value you can use.",
                store=False)
    null_value=fields.Char(
                'Null Value',
                help="This Value is used if the field is empty.",
                size=50, store=False)
    copyvalue=fields.Char(
                'Expression',
                size=100,
                help="Copy and paste the value in the "
                "location you want to use a system value.",
                store=False)
        #Table Fields
    table_model_object_field=fields.Many2one(
                'ir.model.fields',
                string="Table Field",
                help="Select the field from the model you want to use."
                "\nOnly one2many & many2many fields can be used for tables.",
                store=False)
    table_sub_object=fields.Many2one(
                'ir.model',
                'Table-model',
                help="This field shows the model you will "
                "be using for your table.", store=False)
    table_required_fields=fields.Many2many(
                'ir.model.fields',
                'fields_table_rel',
                'field_id', 'table_id',
                string="Required Fields",
                help="Select the fields you require in the table.",
                store=False)
    table_html=fields.Text(
                'HTML code',
                help="Copy this html code to your HTML message "
                "body for displaying the info in your mail.",
                store=False)
    send_on_create= fields.Boolean(
                'Send on Create',
                help='Sends an e-mail when a new document is created.')
    send_on_write= fields.Boolean(
                'Send on Update',
                help='Sends an e-mail when a document is modified.')
    partner_event= fields.Char(
                'Partner ID to log Events',
                size=250,
                help="Partner ID who an email event is logged.\n"
                "Placeholders can be used here. eg. ${object.partner_id.id}\n"
                "You must install the mail_gateway module to see the mail events "
                "in partner form.\nIf you also want to record the link to the "
                "object that sends the email, you must to add this object in the "
                "'Administration/Low Level Objects/Requests/Accepted Links in "
                "Requests' menu (or 'ir.attachment' to record the attachments).")
    template_language=fields.Selection(
                TEMPLATE_ENGINES,
                'Templating Language',
                required=True
                )
    single_email= fields.Boolean("Single email", help="Check it if you want to send a single email for several records (the optional attachment will be generated as a single file for all these records). If you don't check it, an email with its optional attachment will be send for each record.")
    use_filter=fields.Boolean(
                    'Active Filter',
                    help="This option allow you to add a custom python filter"
                    " before sending a mail")
    filter=fields.Text(
                    'Filter',
                    help="The python code entered here will be excecuted if the"
                    "result is True the mail will be send if it false the mail "
                    "won't be send.\n"
                    "Example : o.type == 'out_invoice' and o.number and o.number[:3]<>'os_' ")

    _sql_constraints = [
        ('name', 'unique (name)', _('The template name must be unique!'))
    ]

    def update_auto_email(self):
        pass

    def update_send_on_store(self, cr, uid, ids, context):
        pass

    def create(self):
        pass








# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
