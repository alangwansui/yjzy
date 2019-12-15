# © 2018-Today Aktiv Software (http://www.aktivsoftware.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class SaleOrder(models.Model):
    """Updated new model in the model."""

    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        """A boolean field is added for checking it is sale or not."""
        res = super(SaleOrder, self).action_confirm()
        stock_condition = self.env['stock.picking'].search(
            [('sale_id', '=', self.name)])
        for i in stock_condition:
            i.is_sale = True
        return res
