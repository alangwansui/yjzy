# -*- coding: utf-8 -*-
from odoo import http

# class MultiSelectProductPurchase(http.Controller):
#     @http.route('/multi_select_product_purchase/multi_select_product_purchase/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/multi_select_product_purchase/multi_select_product_purchase/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('multi_select_product_purchase.listing', {
#             'root': '/multi_select_product_purchase/multi_select_product_purchase',
#             'objects': http.request.env['multi_select_product_purchase.multi_select_product_purchase'].search([]),
#         })

#     @http.route('/multi_select_product_purchase/multi_select_product_purchase/objects/<model("multi_select_product_purchase.multi_select_product_purchase"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('multi_select_product_purchase.object', {
#             'object': obj
#         })