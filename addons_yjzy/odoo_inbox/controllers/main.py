# -*- coding: utf-8 -*-
import base64
import werkzeug
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

import odoo
from odoo import http
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class WebsiteOdooInbox(http.Controller):

    _message_per_page = 50

    def _render_odoo_message(self, domain=[], link='/odoo', page=1, label=None, color='#4285F4', search=None, existing_tag=None, existing_folder=None):
        if not label:
            label = 'inbox'
        if label == 'inbox':
            domain += [('folder_id', '=', False)]
        MailMessage = request.env['mail.message'].sudo()
        all_message = MailMessage.search(domain)
        total = len(all_message)
        pager = request.website.pager(
            url=link,
            total=total,
            page=page,
            step=self._message_per_page,
        )
        today_messages = []
        yesterday_messages = []
        thismonth_messages = []
        more_messages = []
        user_id = request.env.user
        domain += [('model', '!=', False)]
        if label == 'inbox':
            if user_id:
                partner_id = request.env.user.partner_id
                if partner_id:
                    domain += ['|', '|', ('partner_ids', 'in', partner_id.ids), ('needaction_partner_ids', 'in', partner_id.ids), ('starred_partner_ids', 'in', partner_id.ids)]

        mails = MailMessage.search(domain, offset=(page-1)*self._message_per_page, limit=self._message_per_page, order="date desc")
        parent_messages = mails.filtered(lambda self: not self.parent_id)

        # import pdb;pdb.set_trace();
        for msg in parent_messages:
            if datetime.strptime(msg.date, '%Y-%m-%d %H:%M:%S').date() == datetime.today().date() or any(datetime.strptime(i.date, '%Y-%m-%d %H:%M:%S').date() == datetime.today().date() for i in msg.child_ids):
                today_messages.append({'parent_id': msg, 'child_ids': sorted(msg.child_ids, key=lambda r: r.date, reverse=False)})
            elif datetime.strptime(msg.date, '%Y-%m-%d %H:%M:%S').date() == (datetime.today().date() - relativedelta(days=1)) or any(datetime.strptime(i.date, '%Y-%m-%d %H:%M:%S').date() == datetime.today().date() for i in msg.child_ids):
                yesterday_messages.append({'parent_id': msg, 'child_ids': sorted(msg.child_ids, key=lambda r: r.date, reverse=False)})
            elif datetime.strptime(msg.date, '%Y-%m-%d %H:%M:%S').month == datetime.today().month or any(datetime.strptime(i.date, '%Y-%m-%d %H:%M:%S').date() == datetime.today().date() for i in msg.child_ids):
                thismonth_messages.append({'parent_id': msg, 'child_ids': sorted(msg.child_ids, key=lambda r: r.date, reverse=False)})
            else:
                more_messages.append({'parent_id': msg, 'child_ids': sorted(msg.child_ids, key=lambda r: r.date, reverse=False)})

        tag_ids = request.env['message.tag'].sudo().search([])
        folder_ids = request.env['message.folder'].sudo().search([])

        return request.render('odoo_inbox.inbox', {
            'today_messages': today_messages,
            'yesterday_messages': yesterday_messages,
            'thismonth_messages': thismonth_messages,
            'more_messages': more_messages,
            'pager': pager,
            'needaction': len(all_message.filtered('needaction')),
            'total': total,
            'current': (page)*self._message_per_page,
            'previouse': (page-1)*self._message_per_page,
            'starred': label == 'starred' and True or False,
            'done': label == 'done' and True or False,
            'snooze': label == 'snoozed' and True or False,
            'draft': label == 'draft' and True or False,
            'sent': label == 'sent' and True or False,
            'trash': label == 'trace' and True or False,
            'label': label,
            'color': color,
            'search': search,
            'tag_ids': tag_ids,
            'existing_tag': existing_tag,
            'folder_ids': folder_ids,
            'existing_folder': existing_folder,
        })

    @http.route(['/odoo/message_read'], type='json', auth="public", website=True)
    def odoo_message_read(self, **kw):
        message = request.env['mail.message'].browse(kw.get('message'))
        for m in message:
            m.msg_unread = True
        return {'msg_unread': True}

    @http.route(['/odoo/inbox',
                 '/odoo/inbox/page/<int:page>',
                 '/odoo/search_message'
                 ], type='http', auth="public", website=True)
    def odoo_inbox(self, page=1, **kw):
        # import pdb;pdb.set_trace();
        search = None
        if kw.get('search'):
            domain = ['|', '|', '|',
                      ('subject', 'ilike', kw.get('search')),
                      ('email_from', 'ilike', kw.get('search')),
                      ('body', 'ilike', kw.get('search')),
                      ('tag_ids.name', 'ilike', kw.get('search'))]
            search = kw.get('search')
        else:
            domain = [('message_label', 'in', ['starred', 'inbox'])]
        return self._render_odoo_message(domain, '/odoo/inbox', page, 'inbox', search=search)

    @http.route(['/odoo/message_post'], type='http', auth="public", website=True)
    def message_post_send(self, **post):
        subject = post.get('subject')
        body = post.get('body')
        messageObj = request.env['mail.message'].browse(int(post.get('message_id')))
        ObjectRecord = request.env[str(messageObj.model)].browse(messageObj.res_id)
        files = request.httprequest.files.getlist('attachments')
        attachment_ids = []
        if files:
            for i in files:
                if i.filename != '':
                    attachments = {
                            'name': i.filename,
                            'res_name': i.filename,
                            'res_model': str(messageObj.model),
                            'res_id': messageObj.res_id,
                            'datas': base64.encodestring(i.read()),
                            'datas_fname': i.filename,
                        }
                    attachment = request.env['ir.attachment'].sudo().create(attachments)
                    attachment_ids.append(attachment.id)

        partner_ids = []
        if post.get('users_ids'):
            users_ids = post.get('users_ids').split(',')
            partner_ids = map(int, users_ids)

        message = ObjectRecord.message_post(
            body=body,
            subject=subject,
            email_from='%s <%s>' % (request.env.user.name, request.env.user.email),
            message_type=messageObj.message_type,
            author_id=request.env.user.partner_id.id,
            parent_id=messageObj.id,
            subtype_id=messageObj.subtype_id.id,
            attachment_ids=attachment_ids,
            partner_ids=partner_ids
        )
        messageObj.msg_unread = False
        message.msg_unread = False
        return request.redirect('/odoo/inbox')

    @http.route(['/sent_mail/odoo'], type='http', auth="public", website=True)
    def mail_send(self, **post):
        if post:
            partners = request.httprequest.form.getlist('partners')
            if partners:
                post['partners_list'] = map(int, partners)
            subject = post.get('subject')
            body = post.get('body')
            for partner in request.env['res.partner'].browse(map(int, partners)):
                message = partner.message_post(
                    body=body,
                    subject=subject,
                    model='res.partner',
                    res_id=partner.id,
                    email_from='%s <%s>' % (request.env.user.name, request.env.user.email),
                    author_id=request.env.user.partner_id.id,
                    partner_ids=[partner.id],
                    message_type='email',
                )
                message.msg_unread = False
                # )
        return request.redirect('/odoo/inbox')

    @http.route(['/odoo/send/<model("mail.message"):message>',
                 ], type='http', auth="public", website=True)
    def odoo_move_send(self, message=None, **post):
        message = request.env['odoo.inbox'].move_to_send(message)
        return request.redirect('/odoo')

    @http.route(['/odoo/send',
                 '/odoo/send/page/<int:page>'
                 ], type='http', auth="public", website=True)
    def odoo_send(self, page=1, **kw):
        domain = [('author_id', '=', request.env.user.partner_id.id), ('message_type', '=', 'email')]
        return self._render_odoo_message(domain, '/odoo/send', page, 'sent', '#898984')

    @http.route(['/odoo/starred/message',
                 ], type='json', auth="public", website=True)
    def message_starred(self, **kw):
        message = request.env['mail.message'].browse(kw.get('message'))
        if kw.get('action') == 'add':
            message.starred_partner_ids = [(4, request.env.user.partner_id.id)]
            request.env['odoo.inbox'].set_star(kw.get('action'), message)
        if kw.get('action') == 'remove':
            message.starred_partner_ids = [(2, request.env.user.partner_id.id)]
            request.env['odoo.inbox'].set_star(kw.get('action'), message)

    @http.route(['/odoo/starred',
                 '/odoo/starred/page/<int:page>'
                 ], type='http', auth="public", website=True)
    def odoo_starred(self, page=1, **kw):
        domain = [('message_label', '=', 'starred')]
        return self._render_odoo_message(domain, '/odoo/starred', page, 'starred', '#f9bd3d')

    @http.route(['/odoo/starred_move_to_inbox/<model("mail.message"):message>',
                 ], type='http', auth="public", website=True)
    def starred_move_to_inbox(self, message=None, **kw):
        message.message_label = 'inbox'
        return request.redirect('/odoo/starred')

    @http.route(['/odoo/snoozed',
                 '/odoo/done/page/<int:page>'
                 ], type='http', auth="public", website=True)
    def odoo_snoozed(self, page=1, **kw):
        domain = [('message_label', '=', 'snoozed')]
        return self._render_odoo_message(domain, '/odoo/snoozed', page, 'snoozed', '#ef6c00')

    @http.route(['/odoo/snoozed/<model("mail.message"):message>',
                 ], type='http', auth="public", website=True)
    def set_snoozed(self, message=None, your_time=None, **post):
        message.message_label = 'snoozed'
        your_time = str(your_time)
        if your_time == 'today':
            message.snoozed_time = datetime.now() + timedelta(hours=2)
        elif your_time == 'tomorrow':
            message.snoozed_time = datetime.now() + timedelta(days=1)
        elif your_time == 'nexweek':
            message.snoozed_time = datetime.now() + timedelta(days=7)
        if post.get('date'):
            message.snoozed_time = datetime.strptime(str(post.get('date')), "%m/%d/%Y %I:%M %p").strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        return request.redirect('/odoo')

    @http.route(['/odoo/set_done/<model("mail.message"):message>',
                 ], type='http', auth="public", website=True)
    def message_done(self, message=None, **kw):
        request.env['odoo.inbox'].set_done(message)
        return request.redirect('/odoo/inbox')

    @http.route(['/odoo/done',
                 '/odoo/done/page/<int:page>'
                 ], type='http', auth="public", website=True)
    def mail_done(self, page=1, **kw):
        domain = [('message_label', '=', 'done')]
        return self._render_odoo_message(domain, '/odoo/done', page, 'done', '#0f9d58')

    @http.route(['/odoo/move_to_inbox/<model("mail.message"):message>',
                 ], type='http', auth="public", website=True)
    def move_to_inbox(self, message=None, **kw):
        message.message_label = 'inbox'
        return request.redirect('/odoo/inbox')

    @http.route([
        '/odoo/move_to_trash/<model("mail.message"):message>',
    ], type='http', auth="public", website=True)
    def odoo_move_trash(self, message=None, **post):
        message = request.env['odoo.inbox'].move_to_trash(message)
        return request.redirect('/odoo/inbox')

    @http.route(['/odoo/trash',
                 '/odoo/trash/page/<int:page>'
                 ], type='http', auth="public", website=True)
    def odoo_trash(self, page=1, **kw):
        domain = [('message_label', '=', 'trace')]
        return self._render_odoo_message(domain, '/odoo/trash', page, 'trace', '#898984')

    @http.route('/odoo/attachment/<model("ir.attachment"):attachment>/download', type='http', website=True)
    def slide_download(self, attachment):
        filecontent = base64.b64decode(attachment.datas)
        main_type, sub_type = attachment.mimetype.split('/', 1)
        disposition = 'attachment; filename=%s.%s' % (werkzeug.urls.url_quote(attachment.name), sub_type)
        return request.make_response(
            filecontent,
            [('Content-Type', attachment.mimetype),
             ('Content-Length', len(filecontent)),
             ('Content-Disposition', disposition)])
        return request.render("website.403")

    @http.route('/odoo/partner_create', type="json", auth="public", website=True)
    def odoo_partner_create(self, email_address, **post):
        if email_address:
            partner_id = request.env['res.partner'].sudo().create({'name': email_address.split('@')[0],
                                                                   'email': email_address})
            return {'success': True, 'partner_id': partner_id.id, 'partner_name': partner_id.name}
        else:
            return {'error': 'email address is wrong'}

    @http.route('/odoo/message_tag_assign', type="json", auth="public", website=True)
    def odoo_message_tag_assign(self, message_id, tag_ids=[], create_tag_input=None, **post):
        if message_id:
            message = request.env['mail.message'].sudo().browse(message_id)
            if create_tag_input:
                new_tag_id = request.env['message.tag'].sudo().create({'name': create_tag_input})
                tag_ids += [new_tag_id.id]
            message.tag_ids = [(6, 0, tag_ids)]
            main_tag_ids = request.env['message.tag'].sudo().search([])
            message_tag_list_template = request.env.ref('odoo_inbox.message_tag_list').render({'mail_message': message})
            message_tag_dropdown = request.env.ref('odoo_inbox.tag_dropdown').render({'mail_message': message, 'tag_ids': main_tag_ids})
            return {'success': True, 'message_tag_list': message_tag_list_template, 'message_tag_dropdown': message_tag_dropdown}
        else:
            return {'error': 'Message is not find'}

    @http.route('/odoo/message_tag_delete', type="json", auth="public", website=True)
    def odoo_message_tag_delete(self, message_id, tag_id, **post):
        if message_id and tag_id:
            message = request.env['mail.message'].sudo().browse(message_id)
            message.tag_ids = [(3, tag_id)]
            main_tag_ids = request.env['message.tag'].sudo().search([])
            message_tag_list_template = request.env.ref('odoo_inbox.message_tag_list').render({'mail_message': message})
            message_tag_dropdown = request.env.ref('odoo_inbox.tag_dropdown').render({'mail_message': message, 'tag_ids': main_tag_ids})
            return {'success': True, 'message_tag_list': message_tag_list_template, 'message_tag_dropdown': message_tag_dropdown}
        else:
            return {'error': 'Message is not find'}

    @http.route(['/odoo/tag/<model("message.tag"):tag>'], type='http', auth="public", website=True)
    def odoo_tags(self, tag, **kw):
        domain = [('tag_ids', '=', tag.id)]
        page = 1
        return self._render_odoo_message(domain, '/odoo/tag/' + str(tag.id), page, tag.name, '#4285F4', existing_tag=tag.id)

    @http.route(['/odoo/tag_edit'], type='http', auth="public", method=['POST'], website=True)
    def odoo_tags_edit(self, **kw):
        if kw.get('tag_id') and kw.get('tag_name'):
            tag_id = request.env['message.tag'].sudo().browse(int(kw.get('tag_id')))
            tag_id.name = kw.get('tag_name')
        return request.redirect(request.httprequest.referrer or '/odoo/inbox')

    @http.route(['/odoo/tag_delete'], type='http', auth="public", method=['POST'], website=True)
    def odoo_tags_delete(self, **kw):
        if kw.get('tag_id'):
            tag_id = request.env['message.tag'].sudo().browse(int(kw.get('tag_id')))
            tag_id.unlink()
        return request.redirect(request.httprequest.referrer or '/odoo/inbox')

    @http.route(['/odoo/folder/<model("message.folder"):folder>'], type='http', auth="public", website=True)
    def odoo_folders(self, folder, **kw):
        domain = [('folder_id', '=', folder.id)]
        page = 1
        return self._render_odoo_message(domain, '/odoo/folder/' + str(folder.id), page, folder.name, '#4285F4', existing_folder=folder.id)

    @http.route(['/odoo/folder_edit'], type='http', auth="public", method=['POST'], website=True)
    def odoo_folder_edit(self, **kw):
        if kw.get('folder_id') and kw.get('folder_name'):
            folder_id = request.env['message.folder'].sudo().browse(int(kw.get('folder_id')))
            folder_id.name = kw.get('folder_name')
        return request.redirect(request.httprequest.referrer or '/odoo/inbox')

    @http.route(['/odoo/folder_delete'], type='http', auth="public", method=['POST'], website=True)
    def odoo_folder_delete(self, **kw):
        if kw.get('folder_id'):
            folder_id = request.env['message.folder'].sudo().browse(int(kw.get('folder_id')))
            folder_id.unlink()
        return request.redirect('/odoo/inbox')

    @http.route(['/odoo/move_to_folder/<model("message.folder"):folder>/<model("mail.message"):message>'], type='http', auth="public", website=True)
    def odoo_move_to_folder(self, folder, message, **kw):
        if folder and message:
            message.folder_id = folder.id
        return request.redirect(request.httprequest.referrer or '/odoo/inbox')

    @http.route(['/odoo/folder/create'], type='http', auth="public", method="POST", website=True)
    def odoo_new_folder(self, **kw):
        if kw.get('create_folder'):
            folder_id = request.env['message.folder'].sudo().create({'name': kw.get('create_folder')})
            if kw.get('message_id') and folder_id:
                message_id = request.env['mail.message'].sudo().browse(int(kw.get('message_id')))
                message_id.folder_id = folder_id.id
        return request.redirect(request.httprequest.referrer or '/odoo/inbox')
