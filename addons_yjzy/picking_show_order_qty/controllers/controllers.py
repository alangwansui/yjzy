# -*- coding: utf-8 -*-
from odoo import http

# class PickingShowOrderQty(http.Controller):
#     @http.route('/picking_show_order_qty/picking_show_order_qty/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/picking_show_order_qty/picking_show_order_qty/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('picking_show_order_qty.listing', {
#             'root': '/picking_show_order_qty/picking_show_order_qty',
#             'objects': http.request.env['picking_show_order_qty.picking_show_order_qty'].search([]),
#         })

#     @http.route('/picking_show_order_qty/picking_show_order_qty/objects/<model("picking_show_order_qty.picking_show_order_qty"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('picking_show_order_qty.object', {
#             'object': obj
#         })