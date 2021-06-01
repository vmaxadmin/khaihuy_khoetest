# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import api, models, fields, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    shipment_count = fields.Integer('Shipment Count', compute='_compute_shipment_count')
    shipping_ids = fields.One2many('shipping.order.line', 'purchase_id', 'Shipping Order Line')
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
            if rec.shipping_ids and rec.shipping_ids[0].purchase_id:
                shipping_state = rec.shipping_ids[0].spo_id.state
                is_shipped = True
            rec.shipping_state = shipping_state
            rec.is_shipped = is_shipped

    def _compute_shipment_count(self):
        for record in self:
            record.shipment_count = self.env['shipping.order.line'].search_count([('purchase_id', '=', record.id)])
