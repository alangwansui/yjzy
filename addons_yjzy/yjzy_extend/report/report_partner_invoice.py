# -*- coding: utf-8 -*-
from math import ceil
from num2words import num2words
from odoo import api, models


class ParticularReport(models.AbstractModel):
    _name = 'report.yjzy_extend.report_partner_invoice'


    @api.model
    def get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('yjzy_extend.report_partner_invoice')
        return {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': self.env[report.model].browse(docids),
            'num2words': num2words,
            'format_float': self.env['ir.qweb.field.float'].value_to_html,
            'ceil': ceil,
        }