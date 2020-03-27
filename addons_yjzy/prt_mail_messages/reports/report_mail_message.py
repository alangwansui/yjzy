# -*- coding: utf-8 -*-
from math import ceil
from num2words import num2words

from odoo import api, models




class Report_Mail_Message(models.AbstractModel):
    _name = 'report.prt_mail_messages.report_mail_message'

    @api.model
    def get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('prt_mail_messages.report_mail_message')
        return {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': self.env[report.model].browse(docids),
            'num2words': num2words,
        }