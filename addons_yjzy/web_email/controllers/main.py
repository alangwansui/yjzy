# -*- coding: utf-8 -*-
from imapclient import IMAPClient
import re
import base64
import imaplib
import collections
import email.utils
import email.header
from email.header import decode_header
from odoo import http
from dateutil import parser
import odoo.tools as tools
from datetime import datetime
from odoo.http import request
from odoo import SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

imaplib._MAXLINE = 200000

pattern_uid = re.compile('\d+ \(UID (?P<uid>\d+)\)')

def parse_uid(data):
    if isinstance(data, bytes):
        data = data.decode("utf-8")
    match = pattern_uid.match(data)
    return match.group('uid')

def split_list(spl_list, chunk_size):
    result_list = []
    while spl_list:
        result_list.append(spl_list[:chunk_size])
        spl_list = spl_list[chunk_size:]
    return result_list

def filter_email_address(email):
    email = email.strip()
    name = ''
    email_address = ''
    if ' ' in email:
        if '<' in email:
            email_split_list = email.split('<')
            name = email_split_list[0]
            if '>' in email_split_list[1]:
                email_address = email_split_list[1].rpartition('>')[0]
            else:
                email_address = email_split_list[1]
    elif '<' in email and '>' in email:
        email_address_between = email.partition('<')[-1].rpartition('>')[0]
        name = email_address_between
        email_address = email_address_between
    else:
        name = email
        email_address = email
    return tools.ustr(name.strip()), tools.ustr(email_address.strip())

def convert(data):
    if isinstance(data, str):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(convert, data.items()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(convert, data))
    else:
        return data


def parser_header(s ):
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



class webEmail(http.Controller):

    def __init__(self):
        self.list_test = 0
        return super(webEmail, self).__init__()

    def search_domain(self, search):
        return '(OR '\
                '(TO "'+ search +'") OR ' \
                '(TO "'+ search.lower() +'") OR '\
                '(TO "'+ search.upper() +'") OR '\
                '(TO "'+ search.title() +'") OR '\
                '(FROM "'+ search +'") OR '\
                '(FROM "'+ search.lower() +'") OR '\
                '(FROM "'+ search.upper() +'") OR '\
                '(FROM "'+ search.title() +'") OR'\
                '(BODY "'+ search +'") OR'\
                '(BODY "'+ search.lower() +'") OR'\
                '(BODY "'+ search.upper() +'") OR'\
                '(BODY "'+ search.title() +'") OR'\
                '(SUBJECT "'+ search +'") OR'\
                '(SUBJECT "'+ search.title() +'") OR'\
                '(SUBJECT "'+ search.upper() +'")'\
                '(SUBJECT "'+ search.lower() +'"))'

    def search_domain_gmail(self, search):
        return '(OR '\
                'TO "'+ search +'" OR ' \
                'FROM "'+ search +'" OR '\
                'BODY "'+ search +'" '\
                'SUBJECT "'+ search +'")'

    def authenticate_email(self, email_address, password, imap_server):
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_address, password)
        return mail

    def disconnect(self, imap):
        imap.logout()

    def authenticate_mail_server(self, email_address, password, imap_server):
        mail_server = IMAPClient(imap_server, use_uid=True, ssl=True)
        mail_server.login(email_address, password)
        return mail_server

    def folders_filter(self, folder, folders):
        fols = []
        for fol in folders:
            if fol[-1].rsplit("/", 1)[0] == folder[-1]:
                fols.append(fol)
        return fols

    def has_child_without_gmail(self, folder, folders):
        child = {
            'path': folder[-1],
            'name': folder[-1].split("/")[-1],
            'display_top': False,
            'children': []
        }
        if '\\NoInferiors' in folder[0]:
            child.update({'display_top': True})
        if '\\HasChildren' in folder[0]:
            child_list = []
            folders.remove(folder)
            for child_folder in self.folders_filter(folder, folders):
                if len(child_folder[-1].split("/")) == len(folder[-1].split("/")) + 1:
                    child_list.append(self.has_child_without_gmail(child_folder, folders))
                child['children'] = child_list
        return child

    def folderList_without_gmail(self, folders):
        folder_list = []
        for folder in folders:
            if len(folder[-1].split("/")) == 1:
                folder_list.append(self.has_child_without_gmail(folder, folders))
        return folder_list

    def has_child(self, folder,mail_lst, folders,mail_list):
        self.list_test += 1
        mail_lst = mail_lst.decode("utf-8")
        child = {
            'path': mail_lst.split('"/"')[-1].replace('"','').strip(),
            'name': folder[-1].split("/")[-1],
            'display_top':False,
            'children':[]
        }
        new_folder = []
        for element in folder[0]:
            new_element = element.decode("utf-8")
            new_folder.append(new_element)
        new_folder = tuple(new_folder)
        if '\\NoInferiors' in new_folder:
            child.update({'display_top':True})
        if '\\HasChildren' in new_folder:
            child_list = []
            folder_index = folders.index(folder)
            parent_folder_name = folder
            folders.remove(folder)
            for child_folder,chield_list in zip(self.folders_filter(folder,folders),mail_list[self.list_test:]):
                if len(child_folder[-1].split("/")) == len(folder[-1].split("/"))+1:
                    child_list.append(self.has_child(child_folder,chield_list,folders,mail_list))
            child['children'] = child_list
            folders.insert(folder_index, parent_folder_name)
        return child

    def folderList(self, folders, mail_list):
        folder_list = []
        for folder,mail_lst in zip(folders,mail_list):
            if len(folder[-1].split("/")) == 1:
                folder_list.append(self.has_child(folder, mail_lst, folders, mail_list))
        self.list_test = 0
        return folder_list[1:]

    def folder_names(self, mail,list_folders):
        label_list = []
        for label,list_folder in zip(mail.list()[1],list_folders):
            label = bytes(label.decode("utf-8"),"utf-8")
            label = label.decode("utf-8")
            display_text = label.split('"/"')[-1].replace('"','').strip()
            values = list_folder[-1].split(", '/', ")[-1]
            folder_list = [values,display_text]
            if display_text == '[Gmail]':
                pass
            else:
             label_list.append(folder_list)
        return label_list

    @http.route(['/web_emails',
#                  '/web_emails/compose_mail',
                 '/web_emails/folder',
                 '/web_emails/open_record',
#                  '/web_emails/reply',
#                  '/web_emails/reply_to_all',
#                  '/web_emails/forward',
                 '/web_emails/contacts'], type='http', auth='public', website=True)
    def web_email(self, **kwargs):
        if request.uid == request.website.user_id.id:
            return request.redirect('/web/login')
        personal_email_credentials_obj = request.env['personal.email.credentials']
        if not kwargs.get('account_id'):
            personal_email_credentials_ids = personal_email_credentials_obj.sudo().search([('user_id', '=', request.uid), ('default', '=', True)], limit=1, order='id')
        else:
            personal_email_credentials_ids = personal_email_credentials_obj.sudo().browse(int(kwargs.get('account_id')))
        if not personal_email_credentials_ids:
            return request.redirect('/web')
        mail = self.authenticate_email(personal_email_credentials_ids.email_address, personal_email_credentials_ids.password, personal_email_credentials_ids.imap_server)
        mail_server = self.authenticate_mail_server(personal_email_credentials_ids.email_address, personal_email_credentials_ids.password, personal_email_credentials_ids.imap_server)
        folderlist = []
        if personal_email_credentials_ids.imap_server == 'imap.exmail.qq.com':
            folderlist = self.folderList(mail_server.list_folders(), mail.list()[1])
            for one_folder in folderlist:
                if str(one_folder.get('path')) == '[Gmail]':
                    one_folder['path']='[Gmail]/All Mail'
        else:
            folderlist = self.folderList_without_gmail(mail_server.list_folders())
        mail_server.logout()

        import json
        context = {
            'session_info': json.dumps(request.env['ir.http'].session_info())
        }

        return request.render('web_email.web_email', {
#             'labels': label_list,
            'folders': folderlist,
            'account_details': personal_email_credentials_obj.sudo().search([('user_id', '=', request.uid)]),
            'active_account_id': personal_email_credentials_ids,
            'menu_data': request.env['ir.ui.menu'].load_menus(request.debug),
            # 'menu_data': request.registry['ir.ui.menu'].load_menus(request.cr, request.uid, request.debug, context=request.context)
            'session_info': json.dumps(request.env['ir.http'].session_info())
        })

    def fetch_body(self, msg):
        attachments = []
        body = ''
        if msg.is_multipart():
            alternative = False
            for part in msg.walk():
                part_payload = part.get_payload(decode=True)
                if part.get_content_type() == 'multipart/alternative':
                    alternative = True
                if part.get_content_maintype() == 'multipart':
                    continue
                filename=part.get_param('filename', None, 'content-disposition')
                if not filename:
                    filename=part.get_param('name', None)
                if filename:
                    if isinstance(filename, tuple):
                        filename=email.utils.collapse_rfc2231_value(filename).strip()
                    else:
                        filename = email.header.decode_header(filename)[0][0]
                encoding = part.get_content_charset()  # None if attachment
                # 1) Explicit Attachments -> attachments
                if filename or part.get('content-disposition', '').strip().startswith('attachment'):
                    if filename:
                        filename = [filename]
                    else:
                        filename = []
                    if part.get('Content-Type', '') and ' ' in part.get('Content-Type'):
                        filename.append(part.get('Content-Type', '').split(' ')[0])
                    elif part.get('Content-Type', '') and '\r' in part.get('Content-Type'):
                        filename.append(part.get('Content-Type', '').split('\r')[0])
                    else:
                        filename.append(part.get('Content-Type', ''))
                    filename = tuple(filename)
                    if part_payload:
                        part_payload = base64.b64encode(part_payload)
                        part_payload = bytes(part_payload.decode("utf-8"),"utf-8")
                        part_payload = part_payload.decode("utf-8")
                        attachments.append((filename or 'attachment', part_payload.replace('\n', '')))
#                         attachments.append((filename or 'attachment', part_payload.encode('base64').replace('\n', '')))
                    continue
                # 2) text/plain -> <pre/>
                if part.get_content_type() == 'text/plain' and (not alternative or not body):
                    body = tools.append_content_to_html(body, tools.ustr(part_payload,
                                                                         encoding, errors='replace'), preserve=True)
                # 3) text/html -> raw
                elif part.get_content_type() == 'text/html':
                    html = tools.ustr(part.get_payload(decode=True), encoding, errors='replace')
                    if alternative:
                        body = html
                    else:
                        body = tools.append_content_to_html(body, html, plaintext=False)
                # 4) Anything else -> attachment
                else:
                    if part_payload:
                        attachments.append((filename or 'attachment', part_payload.encode('base64').replace('\n', '')))
        else:
            body = msg.get_payload(decode=True)
        return body, attachments

    @http.route(['/create-folder'], type='json', auth='public', website=True)
    def create_folder(self, **kwargs):
        personal_email_credentials_ids = request.env['personal.email.credentials'].sudo().browse(int(kwargs.get('account_id')))
        mail = self.authenticate_email(personal_email_credentials_ids.email_address, personal_email_credentials_ids.password, personal_email_credentials_ids.imap_server)
        mail.create('"' + kwargs.get('new_folder_name') + '"')
        self.disconnect(mail)
        return True

    @http.route(['/delete_folder'], type='json', auth='public', website=True)
    def delete_folder(self, **kwargs):
        personal_email_credentials_ids = request.env['personal.email.credentials'].sudo().browse(int(kwargs.get('account_id')))
        mail = self.authenticate_email(personal_email_credentials_ids.email_address, personal_email_credentials_ids.password, personal_email_credentials_ids.imap_server)
        mail.delete('"' + kwargs.get('folder_name') + '"')
        return True

    @http.route(['/rename_folder'], type='json', auth='public', website=True)
    def rename_folder(self, **kwargs):
        personal_email_credentials_ids = request.env['personal.email.credentials'].sudo().browse(int(kwargs.get('account_id')))
        mail = self.authenticate_email(personal_email_credentials_ids.email_address, personal_email_credentials_ids.password, personal_email_credentials_ids.imap_server)
        mail.rename(kwargs.get('folder_name'), kwargs.get('new_name'))
        return True

    @http.route(['/create-contact'], type='json', auth='public', website=True)
    def create_contact(self, **kwargs):
        kwargs.update({'user_id': request.uid})
        # request.env['contact.contact'].sudo().create(kwargs)
        res_partner_vals = {
            'name': kwargs.get('name') + ' '+ kwargs.get('last_name'),
            'email': kwargs.get('email_address')
        }
        if kwargs.get('company_name'):
            res_partner_vals.update({
                'company_name':kwargs.get('company_name')
            })
        request.env['res.partner'].sudo().create(res_partner_vals)
        return True

    @http.route(['/contact_search_query'], type='json', auth='public', website=True)
    def contact_search_query(self, **kwargs):
        return request.env['ir.ui.view'].render_template('web_email.display_contacts', {'contacts': request.env['contact.contact'].sudo().search([('user_id', '=', request.uid),
                                                  '|',
                                                  ('name', 'ilike', kwargs.get('search_query')),
                                                  '|',
                                                  ('last_name', 'ilike', kwargs.get('search_query')),
                                                  ('email_address', 'ilike', kwargs.get('search_query')),
                                                  ])})

    @http.route(['/search-contacts'], type='json', auth='public', website=True)
    def search_contacts(self, **kwargs):
        return request.env['ir.ui.view'].render_template('web_email.contact_lines', {'contacts': request.env['contact.contact'].sudo().search([('user_id', '=', request.uid)])})
        # return request.website._render('web_email.contact_lines', {'contacts': request.env['contact.contact'].sudo().search([('user_id', '=', request.uid)])})

    @http.route(['/import-contacts'], type='json', auth='public', website=True)
    def import_contacts(self, **kwargs):
        kwargs = convert(kwargs)
        if kwargs and kwargs.get('vals'):
            for vals in kwargs.get('vals'):
                if vals.get('email_address') != 'E-mail Address':
                    contact_id = request.env['contact.contact'].sudo().search([('user_id', '=', request.uid), ('email_address', '=', vals.get('email_address'))])
                    if not contact_id:
                        vals.update({'user_id': request.uid})
                        request.env['contact.contact'].sudo().create(vals)
        return True

    @http.route(['/delete-contacts'], type='json', auth='public', website=True)
    def delete_contacts(self, **kwargs):
        for contact_id in kwargs.get('contact_ids'):
            contact = request.env['contact.contact'].sudo().browse(contact_id)
            contact.unlink()
        return True

    @http.route(['/modal-save-contact'], type='json', auth='public', website=True)
    def modal_save_contact(self, **kwargs):
        contact = request.env['contact.contact'].sudo().browse(kwargs.pop('contact_id'))
        # contact.sudo().write(kwargs)
        res_partner_vals = {}
        if kwargs.get('name') or kwargs.get('last_name'):
            if kwargs.get('name') and kwargs.get('last_name'):
                res_partner_vals.update({
                    'name': kwargs.get('name') + ' ' + kwargs.get('last_name'),
                })
            else:
                if kwargs.get('name'):
                    res_partner_vals.update({
                        'name': kwargs.get('name') + ' ' if contact.last_name else '' + contact.last_name if contact.last_name else '',
                    })
                if kwargs.get('last_name'):
                    res_partner_vals.update({
                        'name': contact.name if contact.name else '' + ' ' if contact.name else '' + kwargs.get('last_name'),
                    })

        if kwargs.get('email_address'):
            res_partner_vals.update({
                'email': kwargs.get('email_address')
            })
        if kwargs.get('company_name'):
            res_partner_vals.update({
                'company_name': kwargs.get('company_name')
            })
        contact.partner_id.sudo().write(res_partner_vals)
        return True

    @http.route(['/edit-contact'], type='json', auth='public', website=True)
    def edit_contact(self, **kwargs):
        return request.env['ir.ui.view'].render_template('web_email.edit_contact', {'contact': request.env['contact.contact'].sudo().browse(kwargs.get('contact_id'))})
        # return request.website._render('web_email.edit_contact', {'contact': request.env['contact.contact'].sudo().browse(kwargs.get('contact_id'))})

    @http.route(['/open-record'], type='json', auth='public', website=True)
    def open_record(self, **kwargs):
        personal_email_credentials_ids = request.env['personal.email.credentials'].sudo().browse(int(kwargs.get('account_id')))
        if personal_email_credentials_ids.imap_server == 'imap.exmail.qq.com':
            if str(kwargs.get('folder_name')) == '[Gmail]':
                kwargs['folder_name'] = '[Gmail]/All Mail'
        mail = self.authenticate_email(personal_email_credentials_ids.email_address, personal_email_credentials_ids.password, personal_email_credentials_ids.imap_server)
#         mail.select(str(kwargs.get('folder_name')))
        mail.select('"' + kwargs.get('folder_name') + '"')
        if not kwargs.get('email_ids'):
            if kwargs.get('search'):
                # result, ids = mail.search(None, self.search_domain(str(kwargs.get('search'))))
                if personal_email_credentials_ids.imap_server == 'imap.exmail.qq.com':
                    result, ids = mail.search(None, self.search_domain_gmail(str(kwargs.get('search'))))
                else:
                    result, ids = mail.search(None, self.search_domain(str(kwargs.get('search'))))
            else:
                result, ids = mail.search(None, "ALL")
            id_list = sorted(map(int, ids[0].split()), key=int, reverse=True)
        else:
            id_list = kwargs.get('email_ids')
        next_issue_record = False
        prev_issue_record = False
        if len(id_list) > 1:
            index_of_last_issue_record = id_list.index(int(kwargs.get('email_id')))
            try:
                next_issue_record = id_list[index_of_last_issue_record - 1]
            except IndexError:
                next_issue_record = id_list[-1]
            try:
                prev_issue_record = id_list[index_of_last_issue_record + 1]
            except IndexError:
                prev_issue_record = id_list[0]
        result, data = mail.fetch(str(kwargs.get('email_id')), "(RFC822)")
        

        msg = email.message_from_bytes(data[0][1])
        to = parser_header(msg['To'])

        
        body, attachments = self.fetch_body(msg)
        reply_to_all_emails = []
        if to and ',' in to:
            for reply_to_all_email in to.split(','):
                name, email_address = filter_email_address(reply_to_all_email.strip())
                if personal_email_credentials_ids.email_address != email_address and email_address:
                    reply_to_all_emails.append(email_address)
        elif to and not ',' in to:
            name, email_address = filter_email_address(to.strip())
            if personal_email_credentials_ids.email_address != email_address and email_address:
                reply_to_all_emails.append(email_address)
        if msg['Cc'] and ',' in msg['Cc']:
            for cc_email in msg['Cc'].split(','):
                name, email_address = filter_email_address(cc_email.strip())
                if personal_email_credentials_ids.email_address != email_address and email_address:
                    reply_to_all_emails.append(email_address)
        elif msg['Cc'] and not ',' in msg['Cc']:
            name, email_address = filter_email_address(msg['Cc'].strip())
            if personal_email_credentials_ids.email_address != email_address and email_address:
                reply_to_all_emails.append(email_address)

        mail_server = self.authenticate_mail_server(personal_email_credentials_ids.email_address,
                                                    personal_email_credentials_ids.password,
                                                    personal_email_credentials_ids.imap_server)



        msg_from_name, msg_from_email = filter_email_address(parser_header(msg['from']))
        res = {
            'subject': parser_header(msg.get('Subject')),
            'reply_to_all_emails': reply_to_all_emails,
            'msg_cc': msg['Cc'],
            'msg_to': to,
            'msg_from_name': msg_from_name,
            'msg_from_email': msg_from_email,
            'date': msg['Date'],
            'body': body,
            'attachments': attachments,
            'next_issue_record': next_issue_record,
            'prev_issue_record': prev_issue_record,
            'email_id': kwargs.get('email_id'),
            'folder_name': kwargs.get('folder_name'),
            'folder_names': kwargs.get('folder_names') or self.folder_names(mail,mail_server.list_folders()),
            'superuser_id': SUPERUSER_ID
        }



        self.disconnect(mail)
        if msg['From']:
            name, email_address = filter_email_address(parser_header(msg['from']))
            res.update({'msg_from_name': name, 'msg_from_email': email_address})
            if request.env['contact.contact'].sudo().search(['|', ('email_address', '=', name), ('name', '=', email_address)]):
                res.update({'contact_exist': True})
            else:
                res.update({'contact_exist': False})
        if msg['Date']:
            res.update({'date' : datetime.strftime(parser.parse(msg['Date']), '%m/%d/%Y %H:%M')})

        return request.env['ir.ui.view'].render_template('web_email.email_form_view', res)
        # return request.website._render('web_email.email_form_view', res)

    @http.route(['/update_record_status'], type='json', auth='public', website=True)
    def update_record_status(self, **kwargs):
        personal_email_credentials_ids = request.env['personal.email.credentials'].sudo().browse(int(kwargs.get('account_id')))
        mail = self.authenticate_email(personal_email_credentials_ids.email_address, personal_email_credentials_ids.password, personal_email_credentials_ids.imap_server)
#         mail.select(str(kwargs.get('folder_name')))
        mail.select('"' + kwargs.get('folder_name') + '"')
        if str(kwargs.get('type')) == 'seen_unseen':
            type = '\Seen'
        elif str(kwargs.get('type')) == 'flag_unflag':
            type = '\Flagged'
        mail.store(str(kwargs.get('email_id')).replace('[','').replace(']','').replace(' ',''),str(kwargs.get('flags')),type) #'+FLAGS'
        return True

    @http.route(['/add_new_line'], type='json', auth='public', website=True)
    def add_new_line(self, **kwargs):
        # return request.website._render('web_email.search_line2', {})
        return request.env['ir.ui.view'].render_template('web_email.search_line2', {})

    @http.route(['/folder_list'], type='json', auth='public', website=True)
    def folder_list(self, **kwargs):
        #         user = request.env['res.users'].browse(request.uid)
        personal_email_credentials_ids = request.env['personal.email.credentials'].sudo().browse(
            int(kwargs.get('account_id')))
        mail = self.authenticate_email(personal_email_credentials_ids.email_address,
                                       personal_email_credentials_ids.password,
                                       personal_email_credentials_ids.imap_server)
        mail_server = self.authenticate_mail_server(personal_email_credentials_ids.email_address,
                                                    personal_email_credentials_ids.password,
                                                    personal_email_credentials_ids.imap_server)
        label_list = []
        label_list2 = []
        folder_list = []
        for folder, mail_lst in zip(mail_server.list_folders(), mail.list()[1]):

            mail_lst = bytes(mail_lst.decode("utf-8"),"utf-8")
            mail_lst = mail_lst.decode("utf-8")
            display_text = mail_lst.split('"/"')[-1].replace('"','').strip()

            flage_select = folder[0][0]

            if flage_select == b'\\NoSelect':
                pass
            else:
                label_list.append(
                {'id': mail_lst.split('"/"')[-1].replace('"', '').strip(),
                  'text': folder[-1].split("/")[-1]})
        
        for label in self.folder_names(mail, mail_server.list_folders()):
                if label[0] == '其他文件夹': continue
                label_list2.append(label)
        self.disconnect(mail)

        return {'label_list': label_list, 'label_list2': label_list2}

    def adv_search_domain(self, kwargs):
        search_str = '('
        if kwargs.get('read_unread') != 'dont_care':
            if kwargs.get('read_unread') == 'unread':
                search_str += 'UnSeen '
            else:
                search_str += 'Seen '
        if kwargs.get('date_to') or kwargs.get('date_from'):
            date_to = ''
            date_from = ''
            if kwargs.get('date_to'):
                date_to = datetime.strftime(datetime.strptime(kwargs.get('date_to'), '%m/%d/%Y'), '%d-%b-%Y')
            if kwargs.get('date_from'):
                date_from = datetime.strftime(datetime.strptime(kwargs.get('date_from'), '%m/%d/%Y'), '%d-%b-%Y')
            if date_to and date_from:
                search_str += '(SINCE "' + date_from + '" BEFORE "' + date_to + '") '
            else:
                if date_to:
                    search_str += '(BEFORE "' + date_to + '") '
                elif date_from:
                    search_str += '(SINCE "' + date_from + '") '
        if kwargs.get('min') > 0:
            search_str += '(LARGER ' + str(int(kwargs.get('min')[0]) * 1000) + ') '
        if kwargs.get('max'):
            search_str += '(SMALLER ' + str(int(kwargs.get('max')[0]) * 1000) + ') '
        if kwargs.get('flagged') != 'dont_care':
            if kwargs.get('flagged') == 'yes':
                search_str += 'FLAGGED '
            else:
                search_str += 'UNFLAGGED '
        if kwargs.get('lines') and len(kwargs.get('lines')) > 1:
            search_str += '('
        for line in kwargs.get('lines'):
            if line.get('field') == 'all_field':
                search_str += self.search_domain(line.get('query'))
            elif line.get('field') == 'to':
                if line.get('and_or') != 'none':
                    if line.get('and_or') == 'or':
                        search_str += 'OR '
                search_str += '(TO "' + line.get('query') + '") '
            elif line.get('field') == 'from':
                if line.get('and_or') != 'none':
                    if line.get('and_or') == 'or':
                        search_str += 'OR '
                search_str += '(FROM "' + line.get('query') + '") '

            elif line.get('field') == 'subject':
                if line.get('and_or') != 'none':
                    if line.get('and_or') == 'or':
                        search_str += 'OR '
                search_str += '(SUBJECT "' + line.get('query') + '") '
            elif line.get('field') == 'cc':
                if line.get('and_or') != 'none':
                    if line.get('and_or') == 'or':
                        search_str += 'OR '
                search_str += '(CC "' + line.get('query') + '") '
        if kwargs.get('lines') and len(kwargs.get('lines')) > 1:
            search_str += ')'
        search_str += ')'
        return search_str

    def adv_search_domain_gmail(self, kwargs):
        search_str = '('
        if kwargs.get('read_unread') != 'dont_care':
            if kwargs.get('read_unread') == 'unread':
                search_str += 'UnSeen '
            else:
                search_str += 'Seen '
        if kwargs.get('date_to') or kwargs.get('date_from'):
            date_to = ''
            date_from = ''
            if kwargs.get('date_to'):
                date_to = datetime.strftime(datetime.strptime(kwargs.get('date_to'), '%m/%d/%Y'), '%d-%b-%Y')
            if kwargs.get('date_from'):
                date_from = datetime.strftime(datetime.strptime(kwargs.get('date_from'), '%m/%d/%Y'), '%d-%b-%Y')
            if date_to and date_from:
                search_str += '(SINCE "' + date_from + '" BEFORE "' + date_to + '") '
            else:
                if date_to:
                    search_str += '(BEFORE "' + date_to + '") '
                elif date_from:
                    search_str += '(SINCE "' + date_from + '") '
        if kwargs.get('min'):
            if not kwargs.get('min')[0]:
                search_str += '(LARGER ' + str(int(0) * 1000) + ') '
            else:
                search_str += '(LARGER ' + str(int(kwargs.get('min')[0]) * 1000) + ') '
                #search_str += '(LARGER ' + str(int(kwargs.get('min')[0]) * 1000) + ') '
        if kwargs.get('max'):
            search_str += '(SMALLER ' + str(int(kwargs.get('max')[0]) * 1000) + ') '
        if kwargs.get('flagged') != 'dont_care':
            if kwargs.get('flagged') == 'yes':
                search_str += 'FLAGGED '
            else:
                search_str += 'UNFLAGGED '
        personal_email_credentials_ids = request.env['personal.email.credentials'].sudo().browse(int(kwargs.get('account_id')))
        if personal_email_credentials_ids.imap_server == 'imap.exmail.qq.com':
            if kwargs.get('has_attachment') != 'dont_care':
                if kwargs.get('has_attachment') == 'yes':
                    search_str += 'X-GM-RAW has:attachment '
        if kwargs.get('lines') and len(kwargs.get('lines')) > 1:
            search_str += '('
        first_time_in_loop = False
        for line in kwargs.get('lines'):
            if line.get('field') == 'all_field':
                search_str += self.search_domain_gmail(line.get('query'))
            elif line.get('field') == 'to':
                if line.get('and_or') != 'none':
                    if line.get('and_or') == 'or':
                        if first_time_in_loop:
                            search_str += ' OR'
                        else:
                            search_str += 'OR '
                    if first_time_in_loop:
                        search_str += ' TO "' + line.get('query') + '"'
                    else:
                        search_str += 'TO "' + line.get('query') + '"'
                else:
                    if first_time_in_loop:
                        search_str += ' TO "' + line.get('query') + '"'
                    else:
                        search_str += 'TO "' + line.get('query') + '"'
            elif line.get('field') == 'from':
                if line.get('and_or') != 'none':
                    if line.get('and_or') == 'or':
                        if first_time_in_loop:
                            search_str += ' OR'
                        else:
                            search_str += 'OR '
                    if first_time_in_loop:
                        search_str += ' FROM "' + line.get('query') + '"'
                    else:
                        search_str += 'FROM "' + line.get('query') + '"'
                else:
                    if first_time_in_loop:
                        search_str += ' FROM "' + line.get('query') + '"'
                    else:
                        search_str += 'FROM "' + line.get('query') + '"'
            elif line.get('field') == 'subject':
                if line.get('and_or') != 'none':
                    if line.get('and_or') == 'or':
                        if first_time_in_loop:
                            search_str += ' OR'
                        else:
                            search_str += 'OR '
                    if first_time_in_loop:
                        search_str += ' SUBJECT "' + line.get('query') + '"'
                    else:
                        search_str += 'SUBJECT "' + line.get('query') + '"'
                else:
                    if first_time_in_loop:
                        search_str += ' SUBJECT "' + line.get('query') + '"'
                    else:
                        search_str += 'SUBJECT "' + line.get('query') + '"'
            elif line.get('field') == 'cc':
                if line.get('and_or') != 'none':
                    if line.get('and_or') == 'or':
                        if first_time_in_loop:
                            search_str += ' OR'
                        else:
                            search_str += 'OR '
                    if first_time_in_loop:
                        search_str += ' CC "' + line.get('query') + '"'
                    else:
                        search_str += 'CC "' + line.get('query') + '"'
                else:
                    if first_time_in_loop:
                        search_str += ' CC "' + line.get('query') + '"'
                    else:
                        search_str += 'CC "' + line.get('query') + '"'
            first_time_in_loop = True
        if kwargs.get('lines') and len(kwargs.get('lines')) > 1:
            search_str += ')'
        search_str += ')'
        return search_str

    @http.route(['/advance-search-data'], type='json', auth='public', website=True)
    def advance_search_data(self, **kwargs):
        kwargs = convert(kwargs)
        personal_email_credentials_ids = request.env['personal.email.credentials'].sudo().browse(
            int(kwargs.get('account_id')))
        mail = self.authenticate_email(personal_email_credentials_ids.email_address,
                                       personal_email_credentials_ids.password, personal_email_credentials_ids.imap_server)

        records_list = []
        if kwargs.get('folder_name'):
            folder_list = kwargs.get('folder_name').split(',')
        else:
            folder_list = []
            for label in mail.list()[1]:
                label = bytes(label.decode("utf-8"),"utf-8")
                label = label.decode("utf-8")
                display_text = label.split('"/"')[-1].replace('"', '').strip()
                if display_text == '[Gmail]':
                    pass
                else:
                    folder_list.append(display_text)
        for folder_name in folder_list:
            folder_records = {}
            mail.select('"' + folder_name + '"')
            # result, ids = mail.search(None, self.adv_search_domain(kwargs))
            if personal_email_credentials_ids.imap_server == 'imap.exmail.qq.com':
                result, ids = mail.search(None, self.adv_search_domain_gmail(kwargs))
            else:
                result, ids = mail.search(None, self.adv_search_domain(kwargs))
            if ids and ids[0]:
                new_id = bytes(ids[0].decode("utf-8"),"utf-8")
                new_id = new_id.decode("utf-8")
                result, data = mail.fetch(new_id.replace(' ', ','), "(BODY.PEEK[HEADER])")
                list_of_folder = []
                folder_records.update({'folder_name': folder_name, 'list_of_records': list_of_folder})
                records_list.append(folder_records)
                if result == 'OK':
                    for e in data:
                        if isinstance(e, bytes):
                            e = bytes(e.decode("utf-8"),"utf-8")
                            e = e.decode("utf-8")
                        if e != ')':
                            e1 = bytes(e[1].decode("utf-8"),"utf-8")
                            e1 = e1.decode("utf-8")
                            msg = email.message_from_string(e1)
                            e2 = bytes(e[0].decode("utf-8"),"utf-8")
                            e2 = e2.decode("utf-8")
                            email_id = e2.split('(')[0].strip()
                            mail_data = {
                                'subject': email.header.decode_header(msg['Subject'])[0][0],
                                'from': msg['From'],
                                'to': msg['To'],
                                'date': msg['Date'],
                                'email_id': email_id,
                                'folder_name': folder_name
                            }
                            if msg['Date']:
                                mail_data.update({'date': datetime.strftime(parser.parse(msg['Date']), '%m/%d/%Y %H:%M')})
                            list_of_folder.append(mail_data)
        return {'html_data': request.env['ir.ui.view'].render_template('web_email.searched_email_lines', {'records_list': records_list})}

    def msg_from_decode(self, mail_from):
        email_from = email.header.decode_header(mail_from)[0]
        if 'UTF' in email_from or 'utf-8' in email_from or 'utf' in email_from :
            email_from = tools.ustr(email_from[0])
            email_from = email_from.replace(email_from.partition('"')[-1].rpartition('"')[0], email.header.decode_header(email_from.partition('"')[-1].rpartition('"')[0])[0][0])
        else:
            email_from = tools.ustr(email_from[0])
        return email_from

    @http.route(['/open-search-record'], type='json', auth='public', website=True)
    def open_search_record(self, **kwargs):
#         user = request.env['res.users'].browse(request.uid)
        personal_email_credentials_ids = request.env['personal.email.credentials'].sudo().browse(int(kwargs.get('account_id')))
        mail = self.authenticate_email(personal_email_credentials_ids.email_address, personal_email_credentials_ids.password, personal_email_credentials_ids.imap_server)
#         mail = self.authenticate_email(user)
#         mail.select(str(kwargs.get('folder_name')))
        mail.select('"' + kwargs.get('folder_name') + '"')

        result, data = mail.fetch(str(kwargs.get('email_id')), "(RFC822)")
        new_data = bytes(data[0][1].decode("utf-8"),"utf-8")
        new_data = new_data.decode("utf-8")
        msg = email.message_from_string(new_data)
        to = ''
        for to_email in email.header.decode_header(msg['To']):
            to += to_email[0] + ' '
        body, attachments = self.fetch_body(msg)

        reply_to_all_emails = []
        if msg['Cc'] and ',' in msg['Cc']:
            for cc_email in msg['Cc'].split(','):
                name, email_address = filter_email_address(cc_email.strip())
                if personal_email_credentials_ids.email_address != email_address and email_address:
                    reply_to_all_emails.append(email_address)
        elif msg['Cc'] and not ',' in msg['Cc']:
            name, email_address = filter_email_address(msg['Cc'].strip())
            if personal_email_credentials_ids.email_address != email_address and email_address:
                reply_to_all_emails.append(email_address)



        mail_server = self.authenticate_mail_server(personal_email_credentials_ids.email_address,
                                                    personal_email_credentials_ids.password,
                                                    personal_email_credentials_ids.imap_server)

        res = {
            'subject': email.header.decode_header(msg['Subject'])[0][0],
            'msg_from': self.msg_from_decode(msg['from']),
            'msg_to': to,

            'msg_cc': msg['Cc'],
            'reply_to_all_emails': reply_to_all_emails,

            'msg_from_email': msg['From'].partition('<')[-1].rpartition('>')[0],
            'date': msg['Date'],
            'body': body,
            'attachments': attachments,
            'email_id': kwargs.get('email_id'),
            'folder_name': kwargs.get('folder_name'),
            # 'folder_names': self.folder_names(mail)
            'folder_names': self.folder_names(mail,mail_server.list_folders()),

        }
        self.disconnect(mail)
        if msg['Date']:
            res.update({'date' : datetime.strftime(parser.parse(msg['Date']), '%m/%d/%Y %H:%M')})
        return request.env['ir.ui.view'].render_template('web_email.search-record-form-view', res)
        # return request.website._render('web_email.search-record-form-view', res)

    @http.route(['/compose-mail'], type='json', auth='public', website=True)
    def compose_mail(self, **kwargs):
        contact_obj = request.env['contact.contact']
        user = request.env['res.users'].browse(request.uid)
        personal_email = request.env['personal.email.credentials'].sudo().browse(int(kwargs.get('account_id'))).email_address
        data = {
            'mail_type': kwargs.get('mail_type'),
            'signature': user.signature,
            'personal_email': personal_email,
        }
        res = {}
        contact_list = []
        reply_email_exist = False
        reply_to_email_exist = False
        partner_email_exist = False
        partner = False;
        if kwargs.get('partner_id'):
            partner = request.env['res.partner'].sudo().browse(int(kwargs.get('partner_id')))
            data.update({'partner_id': partner.id})
            res.update({
                'reply_to': partner.email
            })
        if kwargs.get('contact_id'):
            selected_conatct = contact_obj.sudo().browse(int(kwargs.get('contact_id')))
            res.update({
                'reply_to': selected_conatct.email_address
            })
        for contact in contact_obj.sudo().search([('user_id', '=', request.uid)]):
            text = ''
            if contact.company_name:
                text += contact.company_name + ' '
            if contact.name:
                text += contact.name
            if contact.last_name:
                text += ' ' + contact.last_name
            if contact.email_address:
                text += ' <' + contact.email_address + '>'
            contact_list.append({'id': contact.email_address, 'text': text})
            if 'reply_to' in kwargs and contact.email_address == kwargs.get('reply_to'):
                reply_email_exist = True
            if partner and 'partner_id' in kwargs and contact.email_address == partner.email:
                partner_email_exist = True
        if kwargs.get('partner_id') and not partner_email_exist:
            contact_list.append({'id': partner.email, 'text': partner.email})
        if kwargs.get('email_id'):
            personal_email_credentials_ids = request.env['personal.email.credentials'].sudo().browse(int(kwargs.get('account_id')))
            mail = self.authenticate_email(personal_email_credentials_ids.email_address, personal_email_credentials_ids.password, personal_email_credentials_ids.imap_server)
#             mail = self.authenticate_email(user)
#             mail.select(str(kwargs.get('folder_name')))
            mail.select('"' + kwargs.get('folder_name') + '"')
            result, mail_data = mail.fetch(kwargs.get('email_id'), "(RFC822)")
            msg = email.message_from_string(mail_data[0][1])
            body, attachments = self.fetch_body(msg)
            subject = unicode(email.header.decode_header(msg['Subject'])[0][0], errors='ignore')
            msg_from = self.msg_from_decode(msg['from'])
            msg_to = msg['To']
            inline_body = body
            if not kwargs.get('template_id'):
                inline_body = '<br/><br/><blockquote style="border-left: 2px solid blue; margin-left: 8px; padding-left: 8px; font-size:10pt; color:black; font-family:verdana;">-------- Original Message --------<br/>'\
                + 'Subject: ' + subject + '<br/>'\
                + 'From: ' + msg_from + '<br/>'\
                + 'Date: ' + msg['Date'] + '<br/>'\
                + 'To: ' + msg_to + '<br/><br/>'\
                + unicode(email.header.decode_header(body)[0][0], errors='ignore') + '</blockquote>'
            data.update({'inline_body': inline_body, 'folder_name': str(kwargs.get('folder_name'))})
            if kwargs.get('template_id') == kwargs.get('email_id') or kwargs.get('mail_type') == 'reply' or kwargs.get('mail_type') == 'reply-to-all':

                res.update({
                    'reply_to': kwargs.get('reply_to')
                })
                if not reply_email_exist:
                    contact_list.append({'id': kwargs.get('reply_to'), 'text': kwargs.get('reply_to')})
                if not kwargs.get('template_id') and not subject.startswith( 'Re:' ) and not subject.startswith( 'RE:' ):
                    subject = "Re: " + subject
                if kwargs.get('template_id') or kwargs.get('mail_type') == 'reply-to-all':
                    reply_to_all_pre_selected = []
                    if 'reply_to_all_emails' in kwargs and kwargs.get('reply_to_all_emails'):
                        for reply_to_all_email in eval(kwargs.get('reply_to_all_emails')):
                            contact_list.append({'id': reply_to_all_email, 'text': reply_to_all_email})
                            reply_to_all_pre_selected.append({'id': reply_to_all_email, 'text': reply_to_all_email})
                    res.update({
                        'reply_to_all_emails': reply_to_all_pre_selected
                    })
            elif kwargs.get('mail_type') == 'forward':
                res.update({'attachments': attachments})
                if not subject.startswith( 'Fwd:' ):
                    subject = "Fwd: " + subject

            mail_server = self.authenticate_mail_server(personal_email_credentials_ids.email_address,
                                                        personal_email_credentials_ids.password,
                                                        personal_email_credentials_ids.imap_server)

            data.update({
                'subject': subject,
                'email_id': kwargs.get('email_id') or '',
                # 'folder_names': self.folder_names(mail)
                'folder_names': self.folder_names(mail, mail_server.list_folders()),
            })
            self.disconnect(mail)
        # res.update({'html_data': request.website._render('web_email.compose_mail', data), 'contacts': contact_list})
        res.update({'html_data': request.env['ir.ui.view'].render_template('web_email.compose_mail', data), 'contacts': contact_list})
        return res

    @http.route(['/delete_mail'], type='json', auth='public', website=True)
    def delete_mail(self, **kwargs):
        personal_email_credentials_ids = request.env['personal.email.credentials'].sudo().browse(int(kwargs.get('account_id')))
        mail = self.authenticate_email(personal_email_credentials_ids.email_address, personal_email_credentials_ids.password, personal_email_credentials_ids.imap_server)
        mail.select('"' + kwargs.get('folder_name') + '"')
        if not kwargs.get('email_ids'):
            result, ids = mail.search(None, "ALL")
             
            if ids and ids[0]:
                ids_0 = ids[0].decode("utf-8")
                for num in ids_0.split():
                    mail.store(str(num),'+FLAGS','\\Deleted')
        else:
            for num in kwargs.get('email_ids'):
                mail.store(str(num),'+FLAGS','\\Deleted')

        mail.expunge()
        self.disconnect(mail)
        return True

    def filter_send_mail(self, email_addresses):
        all_email = ''
        all_email_list = []
        if email_addresses:
            if ',' in email_addresses:
                for to_email in email_addresses.split(','):
                    name, email_address = filter_email_address(to_email)
                    all_email += email_address + ','
                    all_email_list.append(email_address)
                all_email.strip().rpartition(',')[0]
            else:
                all_email = email_addresses
                all_email_list.append(email_addresses)
        return all_email, all_email_list

    def child_move_records(self, mail, ids, current_folder, destination_folder):
        resp, data = mail.fetch(ids, "(UID)")
        for res in data:
            res = bytes(res.decode("utf-8"),"utf-8")
            res = res.decode("utf-8")
            msg_uid = parse_uid(res)
            result = mail.uid('COPY', int(msg_uid), str(destination_folder))
            if result[0] == 'OK':
                mov, data = mail.uid('STORE', msg_uid , '+FLAGS', '(\Deleted)')
                mail.expunge()
        return True

    @http.route(['/move-records'], type='json', auth='public', website=True)
    def move_records(self, **kwargs):
        ids = ''
        for id in kwargs.get('email_ids'):
            ids += str(id) + ','
        personal_email_credentials_ids = request.env['personal.email.credentials'].sudo().browse(
            int(kwargs.get('account_id')))
        mail = self.authenticate_email(personal_email_credentials_ids.email_address,
                                       personal_email_credentials_ids.password,
                                       personal_email_credentials_ids.imap_server)
#         mail.select(mailbox=str(kwargs.get('current_folder')), readonly=False)
        mail.select(mailbox='"' + str(kwargs.get('current_folder')) + '"', readonly=False)
        if personal_email_credentials_ids.imap_server == 'imap.exmail.qq.com':
            if str(kwargs.get('destination_folder')) == 'Trash':
                resp, data = mail.fetch(ids[:-1].replace(" ", ""), "(UID)")
                for res in data:
                    msg_uid = parse_uid(res)
                    mail.store(ids[:-1].replace(" ", ""), '+X-GM-LABELS', '\\Trash')
                return True

            if str(kwargs.get('destination_folder')) == 'Bulk Mail':
                kwargs['destination_folder'] = '[Gmail]/Spam'
                resp, data = mail.fetch(ids[:-1].replace(" ", ""), "(UID)")
                for res in data:
                    msg_uid = parse_uid(res)
                    mail.store(ids[:-1].replace(" ", ""), '+X-GM-LABELS', '\\Spam')
                return True

        self.child_move_records(mail, ids[:-1].replace(" ", ""), kwargs.get('current_folder'), kwargs.get('destination_folder'))
        self.disconnect(mail)
        return True

    @http.route(['/print-mail'], type='json', auth='public', website=True)
    def print_mail(self, **kwargs):
        personal_email_credentials_ids = request.env['personal.email.credentials'].sudo().browse(int(kwargs.get('account_id')))
        mail = self.authenticate_email(personal_email_credentials_ids.email_address, personal_email_credentials_ids.password, personal_email_credentials_ids.imap_server)
#         mail.select(str(kwargs.get('folder_name')))
        mail.select('"' + kwargs.get('folder_name') + '"')


        result, data = mail.fetch(str(kwargs.get('email_id')).replace('[','').replace(']','').replace(' ',''), "(RFC822)")
        str_html = """
            <table border="0" cellpadding="5" cellspacing="0" width="100%">
                <tbody><tr>
                  <td>
                   <strong><a z-index="50" href="#" onclick="window.print(); return false;">Print</a></strong>
                   &nbsp; | &nbsp;
                   <strong><a href="#" onclick="window.close(); return false;">Close Window</a></strong>
                  </td>
                </tr>
            </tbody></table>
        """
        for e in data:
            if isinstance(e, bytes):
                e = e.decode("utf-8")
            if e != ')':
                e1 = e[1].decode("utf-8")
                msg = email.message_from_string(e1)
                e0 = e[0].decode('utf-8')
                email_id = e0.split('(')[0].strip()
                to = ''
                for to_email in email.header.decode_header(msg['To']):
                    if to_email:
                        to += to_email[0] + ' '
                reply_to_all_emails = []
                if to and ',' in to:
                    for reply_to_all_email in to.split(','):
                        name, email_address = filter_email_address(reply_to_all_email.strip())
                        if personal_email_credentials_ids.email_address != email_address and email_address:
                            reply_to_all_emails.append(email_address)
                elif to and not ',' in to:
                    name, email_address = filter_email_address(to.strip())
                    if personal_email_credentials_ids.email_address != email_address and email_address:
                        reply_to_all_emails.append(email_address)
                if msg['Cc'] and ',' in msg['Cc']:
                    for cc_email in msg['Cc'].split(','):
                        name, email_address = filter_email_address(cc_email.strip())
                        if personal_email_credentials_ids.email_address != email_address and email_address:
                            reply_to_all_emails.append(email_address)
                elif msg['Cc'] and not ',' in msg['Cc']:
                    name, email_address = filter_email_address(msg['Cc'].strip())
                    if personal_email_credentials_ids.email_address != email_address and email_address:
                        reply_to_all_emails.append(email_address)
                body, attachments = self.fetch_body(msg)
                str_html += '<strong>Subject: '+ (email.header.decode_header(msg['Subject'])[0][0])+'</strong><br/>'
                str_html += '<strong>From: '+self.msg_from_decode(msg['from'])+'</strong><br/>'
                str_html += '<strong>Date: '+msg['Date']+'</strong><br/>'
                str_html += '<strong>To: '+msg['To']+'</strong><br/>'
                str_html += '<div style="width:98%;border:1px solid gray;padding:10px;">'+body+'</div>'
                str_html += "<br/><br/>"
        return {"str_html":str_html}

    @http.route(['/save-mail'], type='json', auth='public', website=True)
    def save_mail(self, **kwargs):
        file_list = []
        personal_email_credentials_ids = request.env['personal.email.credentials'].sudo().browse(int(kwargs.get('account_id')))
        mail = self.authenticate_email(personal_email_credentials_ids.email_address, personal_email_credentials_ids.password, personal_email_credentials_ids.imap_server)
#         mail.select(str(kwargs.get('folder_name')))
        mail.select('"' + kwargs.get('folder_name') + '"')
        for num in kwargs.get('email_id'):
            typ, data = mail.fetch(num, '(RFC822)')
            file_list.append({'file_data': data[0][1].encode("base64"), 'subject': 'email_' + str(num)+ '.eml'})
        return {"files":file_list}

    @http.route(['/emails'], type='json', auth='public', website=True)
    def emails(self, **kwargs):
        email_list = []
        page = int(kwargs.get('page'))
        step = int(kwargs.get('step'))
        personal_email_credentials_ids = request.env['personal.email.credentials'].sudo().browse(
            int(kwargs.get('account_id')))

        if personal_email_credentials_ids.imap_server == 'imap.exmail.qq.com':
            if tools.ustr(kwargs.get('folder_name')) == '[Gmail]':
                kwargs['folder_name'] = '[Gmail]/All Mail'

        mail = self.authenticate_email(personal_email_credentials_ids.email_address,
                                       personal_email_credentials_ids.password,
                                       personal_email_credentials_ids.imap_server)

        if kwargs.get('search'):
            if not kwargs.get('folder_name'):
                mail.select('INBOX')
            else:
                mail.select('"' + kwargs.get('folder_name') + '"')
#                 mail.select(str(kwargs.get('folder_name')))
            if 'email_ids' not in kwargs and not kwargs.get('email_ids'):
                # result, ids = mail.search(None, self.search_domain(str(kwargs.get('search'))))
                if personal_email_credentials_ids.imap_server == 'imap.exmail.qq.com':
                    result, ids = mail.search(None, self.search_domain_gmail(str(kwargs.get('search'))))
                else:
                    result, ids = mail.search(None, self.search_domain(str(kwargs.get('search'))))
            else:
                ids = kwargs.get('email_ids')
        else:
            mail.select('"' + kwargs.get('folder_name') + '"')
            if 'email_ids' not in kwargs and not kwargs.get('email_ids'):
                result, ids = mail.search(None, "ALL")
            else:
                ids = kwargs.get('email_ids')
        result, unseen_ids = mail.search(None, 'UnSeen')
        if unseen_ids and unseen_ids[0]:
            unseen_ids = unseen_ids[0].split()
        result, flagged_ids = mail.search(None, 'Flagged')
        if flagged_ids and flagged_ids[0]:
            flagged_ids = flagged_ids[0].split()
        res = {'step': step, 'header': kwargs.get('folder_name')}
        all_data = {}
        if ids and ids[0]:
            if 'email_ids' not in kwargs and not kwargs.get('email_ids'):
                id_list = sorted(map(int, ids[0].split()), key=int, reverse=True)
            else:
                id_list = ids
            all_data.update({'id_list': id_list})
            list_of_list_ids = split_list(id_list, step)
            str_ids = ''
            if page != 0:
                page -= 1
            for ele in list_of_list_ids[page]:
                str_ids += str(ele) + ','
            result, data = mail.fetch(str_ids, "(BODY.PEEK[HEADER])")
            if result == 'OK':
                data = reversed(data)
                for e in data:
                    if e != b')':
                        e1 =e[1]
                        e2 = e[0].decode("utf-8")
                        msg = email.message_from_bytes(e1)

                        email_id = e2.split('(')[0].strip()
                        unread = False
                        if email_id in unseen_ids:
                            unread = True
                        flagged = False
                        if email_id in flagged_ids:
                            flagged = True
                        to = ''
                        if msg['To']:
                            for to_email in email.header.decode_header(msg['To']):
                                if to_email:
                                    if (isinstance(to_email[0], bytes)):
                                        to_mail = bytes(to_email[0].decode("utf-8"),"utf-8")
                                        to_mail = to_mail.decode("utf-8")
                                    else:
                                        to_mail = to_email[0] 
                                    to += to_mail + ' '
                        reply_to_all_emails = []
                        if to and ',' in to:
                            for reply_to_all_email in to.split(','):
                                name, email_address = filter_email_address(reply_to_all_email.strip())
                                if personal_email_credentials_ids.email_address != email_address and email_address:
                                    reply_to_all_emails.append(email_address)
                        elif to and not ',' in to:
                            name, email_address = filter_email_address(to.strip())
                            if personal_email_credentials_ids.email_address != email_address and email_address:
                                reply_to_all_emails.append(email_address)
                        if msg['Cc'] and ',' in msg['Cc']:
                            for cc_email in msg['Cc'].split(','):
                                name, email_address = filter_email_address(cc_email.strip())
                                if personal_email_credentials_ids.email_address != email_address and email_address:
                                    reply_to_all_emails.append(email_address)
                        elif msg['Cc'] and not ',' in msg['Cc']:
                            name, email_address = filter_email_address(msg['Cc'].strip())
                            if personal_email_credentials_ids.email_address != email_address and email_address:
                                reply_to_all_emails.append(email_address)
                        template_name = ''
                        if msg['Message-Id']:
                            template_name = msg['Message-Id']

                        mail_data = {
                            'subject': parser_header(msg['Subject']),
                            'from': parser_header(msg['From']),
                            'reply_to_all_emails': reply_to_all_emails,
                            'to': parser_header(msg['To']),
                            'date': msg['Date'],
                            'email_id': email_id,
                            'new_mail': unread,
                            'flagged': flagged,
                            'template_name': template_name
                        }

                        if msg['Content-Type'] and msg['Content-Type'].startswith('multipart/mixed;'):
                            mail_data.update({'has_attachment': True})
                        else:
                            mail_data.update({'has_attachment': False})

                        if msg['Date']:
                            try:
                                mail_data.update(
                                    {'date': datetime.strftime(parser.parse(msg['Date']), '%m/%d/%Y %H:%M')})
                            except:
                                mail_data.update({'date': ''})
                        email_list.append(mail_data)
            res.update({
                'pager': request.website.pager(url='/emails', total=len(id_list), page=page + 1, step=step, scope=7,
                                               url_args=kwargs),
                'max_value': len(id_list)
            })

        mail_server = self.authenticate_mail_server(personal_email_credentials_ids.email_address,
                                                    personal_email_credentials_ids.password,
                                                    personal_email_credentials_ids.imap_server)

        folder_name = tools.ustr(kwargs.get('folder_name'))
        labels = self.folder_names(mail, mail_server.list_folders())
        folder_name_1 = ''
        for one_label in labels:
            if folder_name in one_label:
                folder_name_1 = tools.ustr(one_label[0])

        res.update({
            'email_list': email_list,
            # 'folder_name': tools.ustr(kwargs.get('folder_name')),
            'folder_name': folder_name_1,
            # 'folder_name': str(kwargs.get('folder_name')),
            'labels': labels,
            # 'labels': kwargs.get('folder_names') or self.folder_names(mail,mail_server.list_folders()),
            'superuser_id': SUPERUSER_ID
        })
        self.disconnect(mail)
        all_data.update({'html_data': request.env['ir.ui.view'].render_template('web_email.email_lines', res)})
        return all_data

