# -*- coding: utf-8 -*-
from math import ceil
from num2words import num2words

from odoo import api, models
from odoo.addons.yjzy_extend.models.tools import collect_hs_lines


def get_attribute8line(line, attribute_name):
    values = line.product_id.attribute_value_ids.filtered(lambda x: x.attribute_id.name == attribute_name)
    return values and values[0].name or '--'


def get_attribute_info(line, diss_attr_names=['英文表面处理','英文主要材料'], diss_values=[u'/', u'-']):
    line.ensure_one()
    values = line.product_id.attribute_value_ids.filtered(lambda x: x.attribute_id.name not in diss_attr_names)
    values = values.filtered(lambda x: x.name not in diss_values)

    dic_gp_vlues = {}
    for v in values:
        gp_id = v.attribute_group_id
        if gp_id not in dic_gp_vlues:
            dic_gp_vlues[gp_id] = v
        else:
            dic_gp_vlues[gp_id] |= v
    groups = values.mapped('attribute_group_id').sorted(key=lambda x: x.sequence)
    result = ''
    for g in groups:
        values = dic_gp_vlues[g]
        values.sorted(key=lambda x: x.attribute_id)
        s = ','.join(['%s:%s' % (v.attribute_id.name, v.name) or '-' for v in values])
        result += '[%s]%s:' % (g.name, s)
    return result

class ParticularReport(models.AbstractModel):
    _name = 'report.yjzy_extend.report_purchase_contract'




    @api.model
    def get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('yjzy_extend.report_purchase_contract')
        return {
            'doc_ids': docids,
            'doc_model': report.model,
            'docs': self.env[report.model].browse(docids),
            'num2words': num2words,
            'get_attribute8line' : get_attribute8line,
            'get_attribute_info': get_attribute_info,
            'format_float': self.env['ir.qweb.field.float'].value_to_html,
            'ceil': ceil,
            'collect_hs_lines': collect_hs_lines,
        }