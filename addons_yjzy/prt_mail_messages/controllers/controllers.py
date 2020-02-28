# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class ProductDimension(http.Controller):
    @http.route('/mail_mail/have_read/<int:mail_id>', auth='none')
    def mail_mail_eceive(self, mail_id, **kw):
        try:
            mail = request.env["mail.mail"].sudo().browse(mail_id)
            mail.readed = True

        except Exception as e:
            print('======', e)

        return '<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mP4//8/AAX+Av4zEpUUAAAAAElFTkSuQmCC"/>'


