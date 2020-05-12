# -*- coding: utf-8 -*-

from odoo import models, fields, api


class gongsi(models.Model):
    _name = 'gongsi'
    _description = '内部公司'



    name = fields.Char('公司')
    partner_id = fields.Many2one('res.partner', '合作伙伴')


    sequence = fields.Integer(help='Used to order Companies in the company switcher', default=10)



    report_header = fields.Text(string='Company Tagline',
                                help="Appears by default on the top right corner of your printed documents (report header).")
    report_footer = fields.Text(string='Report Footer', translate=True,
                                help="Footer text displayed at the bottom of all reports.")



    account_no = fields.Char(string='Account No.')
    street = fields.Char(translate=True)#compute='_compute_address', inverse='_inverse_street'
    street2 = fields.Char( translate=True)#inverse='_inverse_street2'
    zip = fields.Char()#compute='_compute_address', inverse='_inverse_zip'
    city = fields.Char()#compute='_compute_address', translate=True,  inverse='_inverse_city'
    state_id = fields.Many2one('res.country.state',
                               string="Fed. State")#compute='_compute_address', inverse='_inverse_state',
    bank_ids = fields.One2many('res.partner.bank', 'company_id', string='Bank Accounts',
                               help='Bank accounts related to this company')
    country_id = fields.Many2one('res.country',
                                 string="Country")#compute='_compute_address', inverse='_inverse_country',
    email = fields.Char( store=True)#related='partner_id.email',
    phone = fields.Char(store=True)#related='partner_id.phone',
    website = fields.Char()#related='partner_id.website'
    vat = fields.Char( string="TIN")#related='partner_id.vat',
    company_registry = fields.Char()

    full_name = fields.Char(u'公司全称', translate=True)
    fax = fields.Char(u'传真')

    purchase_image = fields.Binary(u'采购合同章', widget='image')
    sale_image = fields.Binary(u'销售合同章', widget='image')

    company_id = fields.Many2one('res.company',u'公司')
    active = fields.Boolean(u'归档', default=True)



    def _compute_address(self):
        for company in self.filtered(lambda company: company.partner_id):
            address_data = company.partner_id.sudo().address_get(adr_pref=['contact'])
            if address_data['contact']:
                partner = company.partner_id.browse(address_data['contact']).sudo()
                company.update(company._get_company_address_fields(partner))

    def _inverse_street(self):
        for company in self:
            company.partner_id.street = company.street

    def _inverse_street2(self):
        for company in self:
            company.partner_id.street2 = company.street2

    def _inverse_zip(self):
        for company in self:
            company.partner_id.zip = company.zip

    def _inverse_city(self):
        for company in self:
            company.partner_id.city = company.city

    def _inverse_state(self):
        for company in self:
            company.partner_id.state_id = company.state_id

    def _inverse_country(self):
        for company in self:
            company.partner_id.country_id = company.country_id

    @api.model_cr
    def _get_company_address_fields(self, partner):
        return {
            'street'     : partner.street,
            'street2'    : partner.street2,
            'city'       : partner.city,
            'zip'        : partner.zip,
            'state_id'   : partner.state_id,
            'country_id' : partner.country_id,
        }