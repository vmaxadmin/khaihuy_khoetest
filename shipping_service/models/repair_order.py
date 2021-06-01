# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    shipment_count = fields.Integer('Shipment Count', compute='_compute_shipment_count')
    shipping_ids = fields.One2many('shipping.order.line', 'repair_id', 'Shipping Order Line')
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
            if rec.shipping_ids and rec.shipping_ids[0].repair_id:
                shipping_state = rec.shipping_ids[0].spo_id.state
                is_shipped = True
            rec.shipping_state = shipping_state
            rec.is_shipped = is_shipped

    def _compute_shipment_count(self):
        for record in self:
            record.shipment_count = self.env['shipping.order.line'].search_count([('repair_id', '=', record.id)])

    def _compute_amount_total_without_shipment_fee(self):
        self.ensure_one()
        amount_total = 0
        for line in self.fees_lines:
            taxes = line.tax_id.compute_all(line.price_unit, line.repair_id.pricelist_id.currency_id, line.product_uom_qty, line.product_id, line.repair_id.partner_id)
            amount_total += taxes['total_included']
        return amount_total  # TODO: check, and except shipping line fee existed

    def create_shipment_fee_line(self, service, shipment_fee):
        RepairFee = self.env['repair.fee']
        taxes = service.product_id.taxes_id.filtered(lambda t: t.company_id.id == self.company_id.id)
        fee_description = '%s: %s' % (service.name,
                                     service.product_id.name)
        values = {
            'repair_id': self.id,
            'name': fee_description,
            'product_uom_qty': 1,
            'product_uom': service.product_id.uom_id.id,
            'product_id': service.product_id.id,
            'price_unit': shipment_fee,
            'tax_id': [(6, 0, taxes.ids)],
            'is_shipment': True,
        }
        sol = RepairFee.create(values)
        return sol


class RepairFee(models.Model):
    _inherit = 'repair.fee'

    is_shipment = fields.Boolean(string="Is Shipment", default=False)
