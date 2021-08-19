# -*- coding: utf-8 -*-
from odoo.models import BaseModel
from odoo import models, fields, api
from odoo.exceptions import ValidationError

def ParseExcelText(s):
    res = []
    for row in s.split('\n'):
        if not row:
            continue
        line = []
        for cell in row.split('\t'):
            line.append(cell)
        res.append(line)
    return res

class ExcelTextParser(models.TransientModel):
    _name = 'excel.text.parser'
    _description = 'Excel复制文本解析器'

    content = fields.Text('复制内容')

    def apply(self):
        ctx = self.env.context
        active_record = self.env[ctx.get('active_model')].browse(ctx.get('active_id'))
        if hasattr(active_record, 'process_excel_text'):
            try:
                active_record.process_excel_text(ParseExcelText(self.content))
            except Exception as e:
                raise ValidationError('内容解析错误,请检查复制的内容是否和excel样板格式一致: %s' % e)
        else:
            raise ValidationError('模型%s未定义 Excel文本复制  使用方法' % active_record._name)

    def clear(self):
        return {
            'name': 'Excel复制文本解析',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'excel.text.parser',
            'target': 'new',
            'context': self.env.context
        }


def open_excel_text_parser(self):
    return {
        'name': 'Excel复制文本解析',
        'type': 'ir.actions.act_window',
        'view_type': 'form',
        'view_mode': 'form',
        'res_model': 'excel.text.parser',
        'target': 'new',
    }

BaseModel.open_excel_text_parser = open_excel_text_parser

