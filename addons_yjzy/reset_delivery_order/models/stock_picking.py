# © 2018-Today Aktiv Software (http://www.aktivsoftware.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    """Added new field for StockPicking."""

    _inherit = 'stock.picking'

    is_sale = fields.Boolean(string="Is Sale")

    def change_state(self):
        """It will change the state of delivery order from canecl to draft."""
        sale_order_name = self.group_id.name
        sale_order = self.env['sale.order'].search(
            [('name', '=', sale_order_name)])
        if len(sale_order.picking_ids) > 1:
            if sale_order.picking_ids[-1].name == self.name or self.backorder_id:
                order_state = self.group_id.name
                so_state = self.env['sale.order'].search(
                    [('name', '=', order_state)]).state
                if so_state == 'sale':
                    self.state = 'draft'
                    if self.move_lines:
                        for move in self.move_lines:
                            move.state = 'draft'
                    self.action_assign()
                else:
                    raise UserError(
                        _('Order number %s has been cancelled.For making this delivery,first you have to confirm order number %s.') % (order_state, order_state))
            else:
                raise UserError(
                    _('This delivery order has been cancelled permanently.'))
        else:
            if sale_order.picking_ids.name == self.name or self.backorder_id:
                order_state = self.group_id.name
                so_state = self.env['sale.order'].search(
                    [('name', '=', order_state)]).state
                if so_state == 'sale':
                    self.state = 'draft'
                    if self.move_lines:
                        for move in self.move_lines:
                            move.state = 'draft'
                    self.action_assign()
                else:
                    raise UserError(
                        _('Order number %s has been cancelled.For making this delivery,first you have to confirm order number %s.') % (order_state, order_state))
            else:
                raise UserError(
                    _('This delivery order has been cancelled permanently.'))
