# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class ShippingExtraAmount(models.Model):
    _name = 'shipping.extra_amount'

    name = fields.Char('Name')
    amount = fields.Float('Amount')


class ShippingOrder(models.Model):
    _name = 'shipping.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Shipping Order"
    _order = "name desc, id desc"

    name = fields.Char(
        required=True, copy=False, readonly=True, states={'prepare': [('readonly', False)]},
        index=True, default=lambda self: _('New'))
    user_id = fields.Many2one('res.users', 'Responsible', tracking=True, default=lambda self:self.env.user)
    shipper_id = fields.Many2one('hr.employee', string='Shipper', tracking=True)
    scheduled_date = fields.Datetime(default=fields.Datetime.now())
    done_date = fields.Datetime(readonly=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id', readonly=True)
    service_id = fields.Many2one(
        'shipping.service', 'Shipping Service', readonly=True, states={'prepare': [('readonly', False)]},
    default=lambda self: self.env['shipping.service'].search([], limit=1)) or False
    state = fields.Selection([
        ('new', 'Draft'),
        ('open', 'Opening'),
        ('close', 'Closed'),
        ('cancel', 'Cancel')
    ],
        default='new', string='Status', tracking=True)
    service_type = fields.Selection(related='service_id.service_type', string='Service Type', tracking=True)
    partner_source_id = fields.Many2one('res.partner', string='Start Default Address')
    from_address = fields.Char('From Address')
    internal_note = fields.Text()
    total_amount = fields.Float('Total Amount', store=True, compute='_amount_all')
    sp_line_ids = fields.One2many('shipping.order.line', 'spo_id', string='Shipping Order Line')
    team_id = fields.Many2one('crm.team', 'Sales Team',
        change_default=True, check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    @api.depends('sp_line_ids.subtotal')
    def _amount_all(self):
        """
        Compute the total amounts of the SPO.
        """
        for sp in self:
            sp.total_amount = sum(sp.sp_line_ids.filtered(lambda x: x.state != 'cancel').mapped('subtotal'))

    @api.onchange('partner_source_id')
    def onchange_partner_source(self):
        for line in self:
            line.from_address = line.partner_source_id.partner_address \
                if line.partner_source_id and line.partner_source_id.partner_address else ''

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New') or False or '':
            vals['name'] = self.env['ir.sequence'].next_by_code('shipping.order') or _('New')
        result = super(ShippingOrder, self).create(vals)
        return result

    def action_open_shipping_order(self):
        self.ensure_one()
        self.write({'state': 'open'})

    def action_cancel_shipping_order(self):
        self.ensure_one()
        spl_in_process = self.sp_line_ids.filtered(lambda x: x.state != ('prepare', 'cancel'))
        if spl_in_process:
            raise UserError('Can not cancel the Shipping Order that have any line in Done and Shipping state! Close it instead.')
        else:
            for line in spl_in_process:
                line.action_cancel_shipment()
        self.write({'state': 'cancel'})

    def action_close_shipping_order(self):
        spl_in_process = self.sp_line_ids.filtered(lambda x: x.state in ('prepare', 'shipping'))
        if spl_in_process:
            raise UserError(_('Can not close the shipping order! You must complete the order line first.'))
        else:
            for line in spl_in_process:
                line.action_cancel_shipment()
        self.write({'state': 'close'})

    def action_reset_shipping_order(self):
        if self.state != 'cancel':
            raise UserError(_('Only reset the shipping order in state Cancel !'))
        self.write({'state': 'new'})

    def unlink(self):
        for ship in self:
            user = self.env.user.has_group('base.group_system')
            if ship.state not in ('new', 'cancel'):
                raise UserError(_('You can not delete the Shipping Order if it is in state %s') % ship.state)
        super(ShippingOrder, self).unlink()


class ShippingOrderLine(models.Model):
    _name = 'shipping.order.line'
    _description = "Shipping Order Line"

    name = fields.Char(compute='_compute_name', store=True)
    sequence = fields.Integer(default=1)
    order_type = fields.Selection([('sale', 'Sale Order'), ('purchase', 'Purchase Order'), ('repair', 'Repair Order')], string='Order Type',
                                  default=False, readonly=True, states={'prepare': [('readonly', False)]})
    sale_id = fields.Many2one('sale.order', 'Sale Order', readonly=True, states={'prepare': [('readonly', False)]}, domain="[('is_shipped', '=', False)]")
    repair_id = fields.Many2one('repair.order', 'Repair Order', readonly=True, states={'prepare': [('readonly', False)]}, domain="[('is_shipped', '=', False)]")
    purchase_id = fields.Many2one('purchase.order', 'Purchase Order', readonly=True, states={'prepare': [('readonly', False)]}, domain="[('is_shipped', '=', False)]")
    partner_source_id = fields.Many2one('res.partner', string='From Partner',
                                        readonly=True, states={'prepare': [('readonly', False)]})
    from_address = fields.Char('From Address',
                               readonly=True, states={'prepare': [('readonly', False)]})
    partner_shipping_id = fields.Many2one('res.partner', string="To Partner",
                                          readonly=True, states={'prepare': [('readonly', False)]})
    to_address = fields.Char('To Address', readonly=True, states={'prepare': [('readonly', False)]})
    phone = fields.Char(store=True, readonly=True, states={'prepare': [('readonly', False)]})
    distance = fields.Float('Distance (Km)', readonly=True, states={'prepare': [('readonly', False)]})
    spo_id = fields.Many2one('shipping.order', string='Shipping Order', readonly=True)
    extra_amount_id = fields.Many2one('shipping.extra_amount', 'Shipping Extra Amount',
                                      readonly=True, states={'prepare': [('readonly', False)]})
    extra_amount = fields.Float('Extra Amount', related='extra_amount_id.amount', store=True)
    amount_fee = fields.Monetary('Amount Fee', currency_field='currency_id',
                                 readonly=True, states={'prepare': [('readonly', False)]})
    subtotal = fields.Float('Amount', store=True, compute='_compute_total_amount')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', 'Currency', related='company_id.currency_id', readonly=True)
    state = fields.Selection([
        ('prepare', 'Prepare'),
        ('shipping', 'Shipping'),
        ('done', 'Done'),
        ('cancel', 'Cancel'),
    ], string='Status', readonly=True, default='prepare', tracking=True,)
    done_date = fields.Datetime(readonly=True)
    service_id = fields.Many2one(related='spo_id.service_id', string='Service', store=True)
    shipper_id = fields.Many2one(string='Shipper', related='spo_id.shipper_id', store=True)
    note = fields.Text()
    team_id = fields.Many2one(related='spo_id.team_id', store=True, string='Sales Team', readonly=True)
    user_id = fields.Many2one(related='spo_id.user_id', store=True, string='Responsible', readonly=True)
    
    @api.onchange('order_type')
    def onchange_order_type(self):
        if self.order_type == 'sale':
            self.repair_id = False
            self.purchase_id = False
        elif self.order_type == 'repair':
            self.sale_id = False
            self.purchase_id = False
        elif self.order_type == 'purchase':
            self.repair_id = False
            self.sale_id = False
        else:
            self.repair_id = False
            self.sale_id = False
            self.purchase_id = False

    @api.depends('spo_id', 'sequence')
    def _compute_name(self):
        for shol in self:
            shol.name = shol.spo_id.name + ' - %s' % shol.sequence

    @api.depends('amount_fee', 'extra_amount')
    def _compute_total_amount(self):
        for line in self:
            line.subtotal = line.amount_fee + line.extra_amount

    @api.onchange('spo_id')
    def _onchange_spo_id(self):
        for line in self:
            sorted_lines = sorted(line.spo_id.sp_line_ids, key=lambda x: x['sequence'], reverse=True)
            if not sorted_lines:
                line.partner_source_id = line.spo_id.partner_source_id or False
            else:
                line.partner_source_id = sorted_lines[0].partner_shipping_id or False

    @api.onchange('sale_id', 'repair_id', 'purchase_id')  # FIXME
    def onchange_sale_id(self):
        for line in self:
            if line.sale_id:
                line.partner_shipping_id = line.sale_id.partner_shipping_id if line.sale_id.partner_shipping_id else ''
            elif line.repair_id:
                line.partner_shipping_id = line.repair_id.address_id if line.repair_id.address_id else ''
            elif line.purchase_id:
                line.partner_shipping_id = line.purchase_id.partner_id if line.purchase_id.partner_id else ''

    @api.onchange('partner_source_id')  # FIXME
    def onchange_partner_source(self):
        for line in self:
            line.from_address = line.partner_source_id.partner_address \
                if line.partner_source_id and line.partner_source_id.partner_address else ''

    @api.onchange('partner_shipping_id')  # FIXME
    def onchange_partner_shipping_id(self):
        for line in self:
            line.phone = line.partner_shipping_id.phone or line.partner_shipping_id.phone or ''
            line.to_address = line.partner_shipping_id.partner_address \
                if line.partner_shipping_id and line.partner_shipping_id.partner_address else ''

    def get_shipment_rate(self):
        res = self.service_id.compute_shipment_rate(self)
        if res.get('success'):
            self.amount_fee = res.get('price') if res.get('price') else 0
            if res.get('distance'):
                self.distance = res.get('distance')
        else:
            raise UserError(_('Have a problem while computing the shipping fee. \n'
                              'Debug message: \n%s') % res.get('error_message'))

    def action_start_shipment(self):
        self.ensure_one()
        # self.action_get_source_address()
        self.get_shipment_rate()
        self.service_id.start_shipment(self)
        if self.service_id.auto_add_fee:
            self._add_shipping_cost_to_order()

    def action_done_shipment(self):
        self.ensure_one()
        self.service_id.done_shipment(self)

    def action_reset_to_draft(self):
        self.ensure_one()
        for line in self:
            if line.spo_id.state != 'open':
                raise UserError('The Shipping Order related this Shipping Line is not opening status !')
        self.service_id.reset_to_draft(self)

    def action_cancel_shipment(self):
        self.ensure_one()
        self.service_id.cancel_shipment(self)

    def _add_shipping_cost_to_order(self):
        self.ensure_one()
        if self.order_type == 'sale':
            amount_excl_ship_fee = self.sale_id._compute_amount_total_without_shipment_fee()
            if self.service_id.free_over and amount_excl_ship_fee > self.service_id.amount_to_free:
                return
            elif self.amount_fee:
                shipment_lines = self.sale_id.order_line.filtered(
                    lambda l: l.is_shipment and l.product_id == self.service_id.product_id)
                shipment_fee = self.amount_fee * (1.0 + (float(self.service_id.margin_percent) / 100))
                if not shipment_lines:
                    self.sale_id.create_shipment_fee_order_line(self.service_id, shipment_fee)
                else:
                    shipment_lines[0].write({
                        'price_unit': shipment_fee + shipment_lines[0].price_unit,
                        'product_uom_qty': 1.0,
                        'name': self.service_id.name,
                    })
        elif self.order_type == 'repair':
            amount_excl_ship_fee = self.repair_id._compute_amount_total_without_shipment_fee()
            if self.service_id.free_over and amount_excl_ship_fee > self.service_id.amount_to_free:
                return
            elif self.amount_fee:
                shipment_lines = self.repair_id.fees_lines.filtered(
                    lambda l: l.is_shipment and l.product_id == self.service_id.product_id)
                shipment_fee = self.amount_fee * (1.0 + (float(self.service_id.margin_percent) / 100))
                if not shipment_lines:
                    self.repair_id.create_shipment_fee_line(self.service_id, shipment_fee)
                else:
                    shipment_lines[0].write({
                        'price_unit': shipment_fee + shipment_lines[0].price_unit,
                        'product_uom_qty': 1.0,
                        'name': self.service_id.name,
                    })

    @api.model
    def create(self, vals):
        if not vals.get('sequence', False):
            spo_id = self.env['shipping.order'].browse(vals.get('spo_id'))
            sp_lines = sorted(spo_id.sp_line_ids, key=lambda x: x['sequence'], reverse=True)
            if sp_lines:
                next_seq = sp_lines[0].sequence + 1
                vals.update({'sequence': next_seq})
        return super(ShippingOrderLine, self).create(vals)

    def unlink(self):
        for line in self:
            if line.state in ('done', 'shipping'):
                raise UserError(_('Can not delete the this shipping line in status Done and Shipping !'))
        return super(ShippingOrderLine, self).unlink()

    def action_show_details_shipping_line(self):
        self.ensure_one()
        view = self.env.ref('shipping_service.shipping_order_line_form_views')
        return {
            'name': _('Shipping Line'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'shipping.order.line',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'current',
            'res_id': self.id,
            'context': dict(self.env.context, create=False)
        }
