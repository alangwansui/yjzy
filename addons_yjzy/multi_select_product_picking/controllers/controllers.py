# -*- coding: utf-8 -*-
from odoo import http

# class MultiSelectProductPicking(http.Controller):
#     @http.route('/multi_select_product_picking/multi_select_product_picking/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/multi_select_product_picking/multi_select_product_picking/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('multi_select_product_picking.listing', {
#             'root': '/multi_select_product_picking/multi_select_product_picking',
#             'objects': http.request.env['multi_select_product_picking.multi_select_product_picking'].search([]),
#         })

#     @http.route('/multi_select_product_picking/multi_select_product_picking/objects/<model("multi_select_product_picking.multi_select_product_picking"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('multi_select_product_picking.object', {
#             'object': obj
#         })