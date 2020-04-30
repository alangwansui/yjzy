# -*- coding: utf-8 -*-
import time
import base64
from odoo import models, fields, api
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import Warning


class Print_Record(models.Model):
    _name = 'print.record'
    _description = '打印记录'

    name = fields.Char('打印记录')
    attachment_ids = fields.Many2many('ir.attachment',  'ref_attachment_print_record',  'pr_id', 'at_id',  '附件')
    res_model = fields.Char('res model')
    res_id = fields.Char('res id')
    report_id = fields.Many2one('ir.actions.report')

    def get(self, record, report):
        one = self.search([('res_model','=', record._name),('res_id', '=', record.id),('report_id','=',report.id)], limit=1)
        if not one:
            one = self.create({
                'name': '%s-%s' % (report.name, record.name_get()[0][1]),
                'res_model': record._name,
                'res_id': record.id,
                'report_id': report.id,
            })
        return one




class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.multi
    def postprocess_pdf_report(self, record, buffer):
        res = super(IrActionsReport, self).postprocess_pdf_report(record, buffer)

        print('===postprocess_pdf_report===', res)

        # if not attachment:
        #     attachment_name = safe_eval(self.attachment, {'object': record, 'time': time})
        #
        #     print('===postprocess_pdf_report2===', attachment_name)
        #     attachment_vals = {
        #         'name': attachment_name,
        #         'datas': base64.encodestring(buffer.getvalue()),
        #         'datas_fname': attachment_name,
        #         'res_model': self.model,
        #         'res_id': record.id,
        #     }
        #     attachment = self.env['ir.attachment'].create(attachment_vals)
        #
        # print_record = self.env['print.record'].get(record, self)
        # print_record.attachment_ids |= attachment

        return res



def get_print_record(self):
    pass

models.BaseModel.get_print_record = get_print_record