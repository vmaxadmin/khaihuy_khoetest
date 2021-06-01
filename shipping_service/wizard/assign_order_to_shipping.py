# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

OrderType = {
    'sale.order': 'sale',
    'repair.order': 'repair',
    'purchase.order': 'purchase',
}


class AssignOrderToShipping(models.TransientModel):
    _name = 'assign.order.2shipping'
    _description = 'Assign Order To Shipping'

    shipping_id = fields.Many2one('shipping.order', 'Shipping', domain="[('state', '=', 'open')]")
    shipper_id = fields.Many2one('hr.employee', 'Shipper')
    note = fields.Text('Note')

    @api.onchange('shipping_id')
    def _onchange_shipping_id(self):
        self.shipper_id = self.shipping_id.shipper_id

    def action_assign_to_shipping_order(self):
        active_id = self._context.get('active_id')
        active_model = self._context.get('active_model', False)
        if not active_id or not active_model or active_model not in ('sale.order', 'repair.order'):
            raise UserError('Exception: Contact to your administrator !')
        object_order = self.env[active_model].browse(active_id)
        address_id = active_model == 'repair.order' and object_order.address_id or object_order.partner_shipping_id
        if active_model == 'repair.order':
            address_id = object_order.address_id
        elif active_model == 'purchase.order':
            address_id = object_order.partner_id
        elif active_model == 'sale.order':
            address_id = object_order.partner_shipping_id
        self.shipping_id.write({'sp_line_ids': [(0, 0, {
            'order_type': OrderType[active_model],
            'sale_id': active_model == 'sale.order' and object_order.id or False,
            'repair_id': active_model == 'repair.order' and object_order.id or False,
            'purchase_id': active_model == 'purchase.order' and object_order.id or False,
            'partner_shipping_id': address_id.id,
            'to_address': address_id.partner_address or '',
            'phone': address_id.phone or address_id.mobile or '',
            'note': self.note,
        })]})
