# -*- coding: utf-8 -*-
import werkzeug
from odoo import http
from odoo.http import request

class ProductDimension(http.Controller):
    @http.route('/mail_mail/have_read/<int:mail_id>', type='http', auth='none', methods=['GET'], csrf=False)
    def mail_mail_eceive(self, mail_id, **kw):
        try:
            print('======mail_mail/have_read=======', request.httprequest.environ['REMOTE_ADDR'])
            ip_address = request.httprequest.environ['REMOTE_ADDR']

            mail = request.env["mail.mail"].sudo().browse(mail_id)

            if ip_address:

                log = request.env['mail.read.log'].sudo().create({
                    'ip_address': ip_address,
                    'mail_id': mail_id,
                    'message_id': mail.mail_message_id.id,
                })
                print('======mail_mail/have_read=======',log)

            mail.readed = True

        except Exception as e:
            print('======', e)


        response = werkzeug.wrappers.Response('<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mP4//8/AAX+Av4zEpUUAAAAAElFTkSuQmCC"/>', mimetype='application/png')
        response.headers.add('Content-Disposition', http.content_disposition('xx.png'))
        return response