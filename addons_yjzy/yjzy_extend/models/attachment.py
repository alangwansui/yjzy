# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import Warning


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    def unlink(self):
        for one in self:
            if one.res_model and one.res_id:
                record = self.env[one.res_model].browse(one.res_id)

                # print('===', record.state)


                if record._name == 'sale.order':
                    if record.state not in ['draft', 'cancel','refuse']:
                        raise Warning('确认的销售订单禁止删除附件')


                elif record._name == 'hr.expense.sheet':
                    if record.state not in ['draft', 'cancel']:
                        raise Warning('审批中禁止删除附件')


                else:
                    pass

        return super(IrAttachment, self).unlink()

