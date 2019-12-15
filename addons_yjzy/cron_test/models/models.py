# -*- coding: utf-8 -*-

from odoo import models, fields, api

class cron_test(models.Model):
    _name = 'cron.test'
    _order = 'id desc'
    _description = u'计划任务测试'
    _rec_name = 'time'

    time = fields.Datetime('time', default=lambda self: fields.datetime.now())

    def run(self):
        self.create({})



