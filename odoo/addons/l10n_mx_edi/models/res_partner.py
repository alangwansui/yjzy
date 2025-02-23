# coding: utf-8

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_mx_edi_addenda = fields.Many2one('ir.ui.view',
        string='Addenda',
        help='A view representing the addenda',
        domain=[('l10n_mx_edi_addenda_flag', '=', True)])
    l10n_mx_edi_addenda_doc = fields.Html(
        string='Addenda Documentation',
        help='How should be done the addenda for this customer (try to put '
        'human readable information here to help the invoice people to '
        'fill properly the fields in the invoice)')
    l10n_mx_edi_colony = fields.Char(string='Colony Name')
    l10n_mx_edi_locality = fields.Char(string='Locality Name')

    @api.model
    def l10n_mx_edi_get_customer_rfc(self):
        """In Mexico depending of some cases the vat (rfc) is not mandatory to be recorded in customers, only for those
        cases instead try to force the record values and make documentation, given a customer the system will propose
        properly a vat (rfc) in order to generate properly the xml following this law:

        http://www.sat.gob.mx/informacion_fiscal/factura_electronica/Documents/cfdi/PyRFactElect.pdf.

        :return: XEXX010101000, XAXX010101000 or the customer vat depending of the country
        """
        self.ensure_one()
        if self.country_id and self.country_id != self.env.ref('base.mx'):
            # Following Question 5 in legal Document.
            return 'XEXX010101000'
        if (self.country_id == self.env.ref('base.mx') or not self.country_id) and not self.vat:
            self.message_post(
                body=_('Using General Public VAT because no vat found'),
                subtype='account.mt_invoice_validated')
            # Following Question 4 in legal Document.
            return 'XAXX010101000'
        # otherwise it returns what customer says and if False xml validation will be solving other cases.
        return self.vat


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    l10n_mx_edi_code = fields.Char(
        'Code', help='Code defined to this position. If this record will be '
        'used as fiscal regime to CFDI, here must be assigned the code '
        'defined to this fiscal regime in the SAT catalog')
