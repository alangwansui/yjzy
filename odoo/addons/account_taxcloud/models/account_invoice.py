# -*- coding: utf-8 -*-

import datetime
import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_round

from .taxcloud_request import TaxCloudRequest

_logger = logging.getLogger(__name__)

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def action_invoice_open(self):
        return super(AccountInvoice, self.with_context(taxcloud_authorize_transaction=True)).action_invoice_open()

    @api.multi
    def invoice_validate(self):
        res = True
        if self.fiscal_position_id.is_taxcloud and self.type in ['out_invoice', 'out_refund']:
            res = self.validate_taxes_on_invoice()
        super(AccountInvoice, self).invoice_validate()
        return res

    def _get_partner(self):
        return self.partner_id

    @api.multi
    def validate_taxes_on_invoice(self):
        Param = self.env['ir.config_parameter']
        api_id = Param.sudo().get_param('account_taxcloud.taxcloud_api_id')
        api_key = Param.sudo().get_param('account_taxcloud.taxcloud_api_key')
        request = TaxCloudRequest(api_id, api_key)

        shipper = self.company_id or self.env.user.company_id
        request.set_location_origin_detail(shipper)
        request.set_location_destination_detail(self._get_partner())

        request.set_invoice_items_detail(self)

        response = request.get_all_taxes_values()

        if response.get('error_message'):
            raise ValidationError(_('Unable to retrieve taxes from TaxCloud: ')+'\n'+response['error_message']+'\n\n'+_('The configuration of TaxCloud is in the Accounting app, Settings menu.'))

        tax_values = response['values']

        raise_warning = False
        for index, line in enumerate(self.invoice_line_ids):
            if line.price_unit >= 0.0:
                price = line.price_unit * (1 - (line.discount or 0.0) / 100.0) * line.quantity
                if not price:
                    tax_rate = 0.0
                else:
                    tax_rate = tax_values[index] / price * 100
                if len(line.invoice_line_tax_ids.ids) > 1 or float_compare(line.invoice_line_tax_ids.amount, tax_rate, precision_digits=3):
                    raise_warning = True
                    tax_rate = float_round(tax_rate, precision_digits=3)
                    tax = self.env['account.tax'].sudo().search([
                        ('amount', '=', tax_rate),
                        ('amount_type', '=', 'percent'),
                        ('type_tax_use', '=', 'sale')], limit=1)
                    if not tax:
                        tax = self.env['account.tax'].sudo().create({
                            'name': 'Tax %.3f %%' % (tax_rate),
                            'amount': tax_rate,
                            'amount_type': 'percent',
                            'type_tax_use': 'sale',
                            'description': 'Sales Tax',
                        })
                    line.invoice_line_tax_ids = tax

        self._onchange_invoice_line_ids()

        if self.type == "out_invoice" and self.env.context.get('taxcloud_authorize_transaction', False):
            request.client.service.Authorized(
                request.api_login_id,
                request.api_key,
                request.customer_id,
                request.cart_id,
                self.id,
                datetime.datetime.now()
            )

        if raise_warning:
            return {'warning': _('The tax rates have been updated, you may want to check it before validation')}
        else:
            return True

    @api.multi
    def action_invoice_paid(self):
        for invoice in self:
            if invoice.fiscal_position_id.is_taxcloud:
                Param = self.env['ir.config_parameter']
                api_id = Param.sudo().get_param('account_taxcloud.taxcloud_api_id')
                api_key = Param.sudo().get_param('account_taxcloud.taxcloud_api_key')
                request = TaxCloudRequest(api_id, api_key)
                if invoice.type == 'out_invoice':
                    request.client.service.Captured(
                        request.api_login_id,
                        request.api_key,
                        invoice.id,
                    )
                else:
                    request.set_invoice_items_detail(self)
                    origin_invoice = self.env['account.invoice'].search([('number', '=', self.origin)], limit=1)
                    if origin_invoice:
                        request.client.service.Returned(
                            request.api_login_id,
                            request.api_key,
                            origin_invoice.id,
                            request.cart_items,
                            fields.Datetime.from_string(self.date_invoice)
                        )
                    else:
                        _logger.warning(_("The source document on the refund is not valid and thus the refunded cart won't be logged on your taxcloud account"))

        return super(AccountInvoice, self).action_invoice_paid()
