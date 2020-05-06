# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning


class res_company(models.Model):
    _inherit = 'res.company'

    full_name = fields.Char(u'公司全称', translate=True)
    fax = fields.Char(u'传真')

    purchase_image = fields.Binary(u'采购合同章', widget='image')
    sale_image = fields.Binary(u'销售合同章', widget='image')

    is_current_date_rate = fields.Boolean(u'是否采用当天汇率')

    gongsi_id = fields.Many2one('gongsi','主体')





    # def test_test(self):
    #     """
    #     设置所有公司字段为1
    #     :return:
    #     """
    #
    #     for f in self.env['ir.model.fields'].search([('ttype','=','many2one'),('relation','=','res.company'),('store','=',True)]):
    #         #print(f.name, f.model_id.model.replace('.', '_'),  f.model_id.name)
    #
    #         table_name  = f.model_id.model.replace('.', '_')
    #         fd_name = f.name
    #
    #         sql = 'update %s set %s = 1' % (table_name, f.name)
    #
    #         try:
    #
    #
    #             self._cr.execute(sql)
    #             self._cr.commit()
    #         except Exception as e:
    #             print('eee', sql, e)





