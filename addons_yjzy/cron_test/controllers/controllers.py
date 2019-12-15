# -*- coding: utf-8 -*-
from odoo import http

# class CronTest(http.Controller):
#     @http.route('/cron_test/cron_test/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/cron_test/cron_test/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('cron_test.listing', {
#             'root': '/cron_test/cron_test',
#             'objects': http.request.env['cron_test.cron_test'].search([]),
#         })

#     @http.route('/cron_test/cron_test/objects/<model("cron_test.cron_test"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('cron_test.object', {
#             'object': obj
#         })