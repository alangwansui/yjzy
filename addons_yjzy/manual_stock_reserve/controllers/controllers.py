# -*- coding: utf-8 -*-
from odoo import http

# class ManualStockReserved(http.Controller):
#     @http.route('/manual_stock_reserved/manual_stock_reserved/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/manual_stock_reserved/manual_stock_reserved/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('manual_stock_reserved.listing', {
#             'root': '/manual_stock_reserved/manual_stock_reserved',
#             'objects': http.request.env['manual_stock_reserved.manual_stock_reserved'].search([]),
#         })

#     @http.route('/manual_stock_reserved/manual_stock_reserved/objects/<model("manual_stock_reserved.manual_stock_reserved"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('manual_stock_reserved.object', {
#             'object': obj
#         })