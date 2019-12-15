# encoding: utf-8
from odoo import api, fields, models, _
from odoo.exceptions import Warning
import logging

_logger = logging.getLogger(__name__)

Business_Lines = [
    ['procurement.order', ],
    ['purchase.order.line', ],
    ['purchase.order', ],

    ['stock.move.line', ],
    ['stock.quant', ],
    ['stock.move', ],
    ['stock.picking', ],
    ['stock.inventory.line', ],
    ['stock.inventory', ],
    ['stock.quant.package', ],
    ['stock.quant.move.rel', ],
    ['stock.production.lot', ],
    ['stock.fixed.putaway.strat', ],
    ['mrp.production.workcenter.line', ],
    ['mrp.production', ],
    ['mrp.production.product.line', ],

    ['sale.order.line', ],
    ['sale.order', ],
    ['pos.order.line', ],
    ['pos.order', ],

    ['account.payment', ],
    ['account.voucher.line', ],
    ['account.voucher', ],
    ['account.invoice', ],
    ['account.partial.reconcile', ],
    ['account.move', ],
    ['account.bank.statement', ],



]

Base_Lines = [
    ['delivery.carrier'],

    ['mrp.bom.line'],
    ['mrp.bom'],

    ['product.product'],
    ['product.template'],
    ['product.category'],
    ['res.partner'],
]


class data_cleaner(models.Model):
    _name = 'data.cleaner'

    name = fields.Char('Name', size=32)
    line_ids = fields.One2many('data.cleaner.line', 'cleaner_id', '模块')

    def create_base_lines(self):
        line_obj = self.env['data.cleaner.line']
        had_names = [x.name for x in self.line_ids]
        for x in Base_Lines:
            name = x[0]
            if name not in had_names:
                line_obj.create({'name': name, 'cleaner_id': self.id, 'save_xml': True})
        self.name = u'基础资料数据'
        return True

    def create_business_lines(self):
        line_obj = self.env['data.cleaner.line']
        had_names = [x.name for x in self.line_ids]
        for x in Business_Lines:
            name = x[0]
            if name not in had_names:
                line_obj.create({'name': name, 'cleaner_id': self.id})
        self.name = u'业务资料数据'
        return True

    def clean_test_data(self):
        for line in self.line_ids:
            line.clean_one()

    def clean_unused_xml_data(self):
        pass


class data_cleaner_line(models.Model):
    _name = 'data.cleaner.line'
    name = fields.Char(u'模型')
    sequence = fields.Integer(u'序号')
    modle_id = fields.Many2one('ir.model')
    cleaner_id = fields.Many2one('data.cleaner', u'清理')
    save_xml = fields.Boolean(u'不删除带外部记录ID的数据')
    note = fields.Text(u'清理结果')

    def clean_one(self):
        self.ensure_one()
        xml_obj = self.env['ir.model.data']
        cr = self._cr
        line = self
        obj = self.env.get(line.name, False)


        if obj == False:
            _logger.info('not found %s, continue' % line.name)
            self.note = 'not found table name'
            return

        if not line.save_xml:
            if obj._table:
                sql = "delete from %s" % obj._table
                cr.execute(sql)
                _logger.info('delete data %s success' % obj._table)
        else:
            xml_ids = xml_obj.search([('model', '=', line.name)]).mapped('id')
            if xml_ids:
                records = self.env[line.name].search([('id', 'not in', xml_ids)])
                records.unlink()
                _logger.info('delete data %s success' % obj._table)
                self.note = 'sucess'
            else:
                sql = "delete from %s" % obj._table
                cr.execute(sql)
                _logger.info('delete data %s success' % obj._table)
                self.note = 'sucess'


