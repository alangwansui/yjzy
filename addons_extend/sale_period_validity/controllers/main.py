# -*- coding: utf-8 -*-
##############################################################################
import base64
import werkzeug
from odoo.http import Controller, route, request
from odoo.exceptions import AccessError
from odoo import exceptions, fields, http, _
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.sale.controllers.portal import CustomerPortal

class sale_quote(CustomerPortal):

    @http.route(['/my/quotes/signed'], type='json', auth="public", website=True)
    def portal_quote_signed(self, res_id, access_token=None, partner_name=None, signature=None):
        if not self._portal_quote_user_can_accept(res_id):
            return {'error': _('Operation not allowed')}
        if not signature:
            return {'error': _('Signature is missing.')}

        try:
            order_sudo = self._order_check_access(res_id, access_token=access_token)
        except AccessError:
            return {'error': _('Invalid order')}

        order_sudo.action_signed()

        _message_post_helper(
            res_model='sale.order',
            res_id=order_sudo.id,
            message=_('Order signed by %s') % (partner_name,),
            attachments=[('signature.png', base64.b64decode(signature))] if signature else [],
            **({'token': access_token} if access_token else {}))
        return {
            'success': _(u'您已经完成对收货的签字'),
            'redirect_url': '/quote/%s/%s' % (order_sudo.id, access_token),
        }



