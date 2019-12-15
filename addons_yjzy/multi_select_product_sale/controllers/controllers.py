# -*- coding: utf-8 -*-
from odoo import http

# class MultiSelectProductSale(http.Controller):
#     @http.route('/multi_select_product_sale/multi_select_product_sale/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/multi_select_product_sale/multi_select_product_sale/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('multi_select_product_sale.listing', {
#             'root': '/multi_select_product_sale/multi_select_product_sale',
#             'objects': http.request.env['multi_select_product_sale.multi_select_product_sale'].search([]),
#         })

#     @http.route('/multi_select_product_sale/multi_select_product_sale/objects/<model("multi_select_product_sale.multi_select_product_sale"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('multi_select_product_sale.object', {
#             'object': obj
#         })