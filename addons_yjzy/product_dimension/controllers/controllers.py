# -*- coding: utf-8 -*-
from odoo import http

# class ProductDimension(http.Controller):
#     @http.route('/product_dimension/product_dimension/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/product_dimension/product_dimension/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('product_dimension.listing', {
#             'root': '/product_dimension/product_dimension',
#             'objects': http.request.env['product_dimension.product_dimension'].search([]),
#         })

#     @http.route('/product_dimension/product_dimension/objects/<model("product_dimension.product_dimension"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('product_dimension.object', {
#             'object': obj
#         })