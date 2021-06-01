# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shipment_count = fields.Integer('Shipment Count', compute='_compute_shipment_count')
    shipping_ids = fields.One2many('shipping.order.line', 'sale_id', 'Shipping Order Line')
    shipping_state = fields.Selection([
        ('new', 'Draft'),
        ('open', 'Opening'),
        ('close', 'Closed'),
        ('cancel', 'Cancel')
    ], string='Shipping State', tracking=True, compute='_compute_shipping_state')
    is_shipped = fields.Boolean('Shipped', default=False, compute='_compute_shipping_state', store=True)

    @api.depends('shipping_ids')
    def _compute_shipping_state(self):
        for rec in self:
            shipping_state = False
            is_shipped = False
            if rec.shipping_ids and rec.shipping_ids[0].sale_id:
                shipping_state = rec.shipping_ids[0].spo_id.state
                is_shipped = True
            rec.shipping_state = shipping_state
            rec.is_shipped = is_shipped

    def _compute_shipment_count(self):
        for record in self:
            record.shipment_count = self.env['shipping.order.line'].search_count([('sale_id', '=', record.id)])

    def _compute_amount_total_without_shipment_fee(self):
        self.ensure_one()
        shipment_cost = sum([l.price_total for l in self.order_line if l.is_shipment])
        # Do not change amount on the existed shipping line of the Sale Order
        return self.amount_total - shipment_cost

    def create_shipment_fee_order_line(self, service, shipment_fee):
        SaleOrderLine = self.env['sale.order.line']
        taxes = service.product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        taxes_ids = taxes.ids
        if self.partner_id and self.fiscal_position_id:
            taxes_ids = self.fiscal_position_id.map_tax(taxes, service.product_id, self.partner_id).ids
        so_description = '%s: %s' % (service.name,
                                     service.product_id.name)
        values = {
            'order_id': self.id,
            'name': so_description,
            'product_uom_qty': 1,
            'product_uom': service.product_id.uom_id.id,
            'product_id': service.product_id.id,
            'price_unit': shipment_fee,
            'tax_id': [(6, 0, taxes_ids)],
            'is_shipment': True,
        }
        sol = SaleOrderLine.create(values)
        return sol


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_shipment = fields.Boolean(string="Is Shipment", default=False)
