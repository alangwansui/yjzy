# -*- coding: utf-8 -*-
from odoo import http

# class YjzyExtend(http.Controller):
#     @http.route('/yjzy_extend/yjzy_extend/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/yjzy_extend/yjzy_extend/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('yjzy_extend.listing', {
#             'root': '/yjzy_extend/yjzy_extend',
#             'objects': http.request.env['yjzy_extend.yjzy_extend'].search([]),
#         })

#     @http.route('/yjzy_extend/yjzy_extend/objects/<model("yjzy_extend.yjzy_extend"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('yjzy_extend.object', {
#             'object': obj
#         })