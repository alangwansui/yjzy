from odoo import models, fields, api,_

class StockPickingDelivery(models.Model):
    _inherit = 'stock.picking'

    delivery_status = fields.Selection([
        ('undelivered','Undelivered'),
        ('received', 'Received')],
        string="Partner Status",
        copy=False,
        default='undelivered')