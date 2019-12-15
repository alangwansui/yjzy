# -*- coding: utf-8 -*-
from odoo import http

# class MultiInvoicePaymentExtend(http.Controller):
#     @http.route('/multi_invoice_payment_extend/multi_invoice_payment_extend/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/multi_invoice_payment_extend/multi_invoice_payment_extend/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('multi_invoice_payment_extend.listing', {
#             'root': '/multi_invoice_payment_extend/multi_invoice_payment_extend',
#             'objects': http.request.env['multi_invoice_payment_extend.multi_invoice_payment_extend'].search([]),
#         })

#     @http.route('/multi_invoice_payment_extend/multi_invoice_payment_extend/objects/<model("multi_invoice_payment_extend.multi_invoice_payment_extend"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('multi_invoice_payment_extend.object', {
#             'object': obj
#         })