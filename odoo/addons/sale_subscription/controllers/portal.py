# -*- coding: utf-8 -*-
import datetime
from collections import OrderedDict
from dateutil.relativedelta import relativedelta
from werkzeug.exceptions import NotFound
from odoo import http
from odoo.http import request
from odoo.tools.translate import _

from odoo.addons.portal.controllers.portal import get_records_pager, pager as portal_pager, CustomerPortal


class CustomerPortal(CustomerPortal):

    def _get_subscription_domain(self, partner):
        return [
            ('partner_id.id', 'in', [partner.id, partner.commercial_partner_id.id]),
            ('state', '!=', 'cancel'),
        ]

    def _prepare_portal_layout_values(self):
        """ Add subscription details to main account page """
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        values['subscription_count'] = request.env['sale.subscription'].search_count(self._get_subscription_domain(partner))
        return values

    @http.route(['/my/subscription', '/my/subscription/page/<int:page>'], type='http', auth="user", website=True)
    def my_subscription(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleSubscription = request.env['sale.subscription']

        domain = self._get_subscription_domain(partner)

        archive_groups = self._get_archive_groups('sale.subscription', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'}
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'open': {'label': _('In Progress'), 'domain': [('state', '=', 'open')]},
            'pending': {'label': _('To Renew'), 'domain': [('state', '=', 'pending')]},
            'close': {'label': _('Closed'), 'domain': [('state', '=', 'close')]},
        }

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # pager
        account_count = SaleSubscription.search_count(domain)
        pager = portal_pager(
            url="/my/subscription",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
            total=account_count,
            page=page,
            step=self._items_per_page
        )

        accounts = SaleSubscription.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_subscriptions_history'] = accounts.ids[:100]

        values.update({
            'accounts': accounts,
            'page_name': 'subscription',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/subscription',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("sale_subscription.portal_my_subscriptions", values)


class sale_subscription(http.Controller):

    @http.route(['/my/subscription/<int:account_id>/',
                 '/my/subscription/<int:account_id>/<string:uuid>'], type='http', auth="public", website=True)
    def subscription(self, account_id, uuid='', message='', message_class='', **kw):
        account_res = request.env['sale.subscription']
        if uuid:
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid or account.state == 'cancelled':
                raise NotFound()
            if request.uid == account.partner_id.user_id.id:
                account = account_res.browse(account_id)
        else:
            account = account_res.browse(account_id)

        acquirers = list(request.env['payment.acquirer'].search([
            ('website_published', '=', True),
            ('registration_view_template_id', '!=', False),
            ('token_implemented', '=', True)]))
        acc_pm = account.payment_token_id
        part_pms = account.partner_id.payment_token_ids
        display_close = account.template_id.sudo().user_closable and account.state != 'close'
        is_follower = request.env.user.partner_id.id in [follower.partner_id.id for follower in account.message_follower_ids]
        active_plan = account.template_id.sudo()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        if account.recurring_rule_type != 'weekly':
            rel_period = relativedelta(datetime.datetime.today(), datetime.datetime.strptime(account.recurring_next_date, '%Y-%m-%d'))
            missing_periods = getattr(rel_period, periods[account.recurring_rule_type]) + 1
        else:
            delta = datetime.datetime.today() - datetime.datetime.strptime(account.recurring_next_date, '%Y-%m-%d')
            missing_periods = delta.days / 7
        dummy, action = request.env['ir.model.data'].get_object_reference('sale_subscription', 'sale_subscription_action')
        values = {
            'account': account,
            'template': account.template_id.sudo(),
            'display_close': display_close,
            'is_follower': is_follower,
            'close_reasons': request.env['sale.subscription.close.reason'].search([]),
            'missing_periods': missing_periods,
            'payment_mandatory': active_plan.payment_mandatory,
            'user': request.env.user,
            'acquirers': acquirers,
            'acc_pm': acc_pm,
            'part_pms': part_pms,
            'is_salesman': request.env['res.users'].sudo(request.uid).has_group('sales_team.group_sale_salesman'),
            'action': action,
            'message': message,
            'message_class': message_class,
            'change_pm': kw.get('change_pm') != None,
            'pricelist': account.pricelist_id.sudo(),
            'submit_class':'btn btn-primary btn-sm mb8 mt8 pull-right',
            'submit_txt':'Pay Subscription',
            'bootstrap_formatting':True,
            'return_url':'/my/subscription/' + str(account_id) + '/' + str(uuid),
        }

        history = request.session.get('my_subscriptions_history', [])
        values.update(get_records_pager(history, account))
        return request.render("sale_subscription.subscription", values)

    payment_succes_msg = 'message=Thank you, your payment has been validated.&message_class=alert-success'
    payment_fail_msg = 'message=There was an error with your payment, please try with another payment method or contact us.&message_class=alert-danger'

    @http.route(['/my/subscription/payment/<int:account_id>/',
                 '/my/subscription/payment/<int:account_id>/<string:uuid>'], type='http', auth="public", methods=['POST'], website=True)
    def payment(self, account_id, uuid=None, **kw):
        account_res = request.env['sale.subscription']
        invoice_res = request.env['account.invoice']
        get_param = ''
        if uuid:
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid:
                raise NotFound()
        else:
            account = account_res.browse(account_id)

        # no change
        if int(kw.get('pm_id', 0)) > 0:
            account.payment_token_id = int(kw['pm_id'])

        # if no payment has been selected for this account, then we display redirect to /my/subscription with an error message
        if len(account.payment_token_id) == 0:
            get_param = 'message=No payment method have been selected for this subscription.&message_class=alert-danger'
            return request.redirect('/my/subscription/%s/%s?%s' % (account.id, account.uuid, get_param))

        # we can't call _recurring_invoice because we'd miss 3DS, redoing the whole payment here
        payment_token = account.payment_token_id
        if payment_token:
            invoice_values = account.sudo()._prepare_invoice()
            new_invoice = invoice_res.sudo().create(invoice_values)
            new_invoice.compute_taxes()
            tx = account.sudo()._do_payment(payment_token, new_invoice)[0]
            if tx.html_3ds:
                return tx.html_3ds
            get_param = self.payment_succes_msg if tx.state in ['done', 'authorized'] else self.payment_fail_msg
            if tx.state in ['done', 'authorized']:
                account.send_success_mail(tx, new_invoice)
                msg_body = 'Manual payment succeeded. Payment reference: <a href=# data-oe-model=payment.transaction data-oe-id=%d>%s</a>; Amount: %s. Invoice <a href=# data-oe-model=account.invoice data-oe-id=%d>View Invoice</a>.' % (tx.id, tx.reference, tx.amount, new_invoice.id)
                account.message_post(body=msg_body)
            else:
                new_invoice.unlink()

        return request.redirect('/my/subscription/%s/%s?%s' % (account.id, account.uuid, get_param))

    # 3DS controllers
    # transaction began as s2s but we receive a form reply
    @http.route(['/my/subscription/<sub_uuid>/payment/<int:tx_id>/accept/',
                 '/my/subscription/<sub_uuid>/payment/<int:tx_id>/decline/',
                 '/my/subscription/<sub_uuid>/payment/<int:tx_id>/exception/'], type='http', auth="public", website=True)
    def payment_accept(self, sub_uuid, tx_id, **kw):
        Subscription = request.env['sale.subscription']
        tx_res = request.env['payment.transaction']

        subscription = Subscription.sudo().search([('uuid', '=', sub_uuid)])
        tx = tx_res.sudo().browse(tx_id)

        tx.form_feedback(kw, tx.acquirer_id.provider)

        get_param = self.payment_succes_msg if tx.state in ['done', 'authorized'] else self.payment_fail_msg

        return request.redirect('/my/subscription/%s/%s?%s' % (subscription.id, sub_uuid, get_param))

    @http.route(['/my/subscription/<int:account_id>/close'], type='http', methods=["POST"], auth="public", website=True)
    def close_account(self, account_id, uuid=None, **kw):
        account_res = request.env['sale.subscription']

        if uuid:
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid:
                raise NotFound()
        else:
            account = account_res.browse(account_id)

        if account.sudo().template_id.user_closable:
            close_reason = request.env['sale.subscription.close.reason'].browse(int(kw.get('close_reason_id')))
            account.close_reason_id = close_reason
            if kw.get('closing_text'):
                account.message_post(_('Closing text : ') + kw.get('closing_text'))
            account.set_close()
            account.date = datetime.date.today().strftime('%Y-%m-%d')
        return request.redirect('/my/home')


    @http.route(['/my/subscription/<int:account_id>/set_pm',
                '/my/subscription/<int:account_id>/<string:uuid>/set_pm'], type='http', methods=["POST"], auth="public", website=True)
    def set_payment_method(self, account_id, uuid=None, **kw):
        account_res = request.env['sale.subscription']
        if uuid:
            account = account_res.sudo().browse(account_id)
            if uuid != account.uuid:
                raise NotFound()
        else:
            account = account_res.browse(account_id)

        if kw.get('pm_id'):
            new_token = request.env['payment.token'].browse(int(kw.get('pm_id')))

            if new_token.verified:
                account.payment_token_id = new_token
                get_param = 'message=Your payment method has been changed for this subscription.&message_class=alert-success'
            else:
                get_param = 'message=Your payment method must be verified to use it on a subscription.&message_class=alert-danger'
        else:
            get_param = 'message=Impossible to change your payment method for this subscription.&message_class=alert-danger'

        return request.redirect('/my/subscription/%s/%s?%s' % (account.id, account.uuid, get_param))