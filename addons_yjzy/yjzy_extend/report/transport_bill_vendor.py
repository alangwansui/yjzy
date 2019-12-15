# -*- coding: utf-8 -*-
from num2words import num2words
from odoo import api, models
from math import ceil
from odoo.addons.yjzy_extend.models.tools import collect_hs_lines


class ParticularReport(models.AbstractModel):
    _name = 'report.yjzy_extend.report_transport_bill_vendor'

    @api.model
    def get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('yjzy_extend.report_transport_bill_vendor')
        return {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': self.env[report.model].browse(docids),
            'num2words': num2words,
            'format_float': self.env['ir.qweb.field.float'].value_to_html,
            'ceil': ceil,
            'collect_hs_lines': collect_hs_lines,
        }