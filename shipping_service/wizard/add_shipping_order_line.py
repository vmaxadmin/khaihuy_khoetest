# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AddShippingSPOL(models.TransientModel):
    _name = 'shipping.order.line.wizard'
    _description = 'Add Shipping Order Line'

    partner_source_id = fields.Many2one('res.partner', string='From Partner')
    from_address = fields.Char(string='From Address')
    order_type = fields.Selection([('sale', 'Sale Order'), ('purchase', 'Purchase'), ('repair', 'Repair Order')], string='Order Type',
                                  default='sale')
    repair_id = fields.Many2one('repair.order', 'Repair Order', domain="[('is_shipped', '=', False)]")
    sale_id = fields.Many2one('sale.order', 'Sale Order', domain="[('is_shipped', '=', False)]")
    purchase_id = fields.Many2one('purchase.order', 'Purchase Order', domain="[('is_shipped', '=', False)]")
    partner_shipping_id = fields.Many2one('res.partner', string="To Partner")
    to_address = fields.Char('To Address')
    phone = fields.Char(related='partner_shipping_id.phone')
    distance = fields.Float('Distance (Km)')
    extra_amount_id = fields.Many2one('shipping.extra_amount', 'Shipping Extra Amount')
    extra_amount = fields.Float('Extra Amount', related='extra_amount_id.amount', store=True)
    spo_id = fields.Many2one('shipping.order', string='Shipping Order')
    note = fields.Text()

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

    @api.onchange('partner_shipping_id')
    def onchange_partner_shipping_id(self):
        for line in self:
            line.to_address = line.partner_shipping_id.partner_address \
                if line.partner_shipping_id and line.partner_shipping_id.partner_address else ''

    @api.onchange('partner_source_id')
    def onchange_partner_source_id(self):
        for line in self:
            line.from_address = line.partner_source_id.partner_address \
                if line.partner_source_id and line.partner_source_id.partner_address else ''

    @api.onchange('sale_id')
    def onchange_sale_id(self):
        for line in self:
            line.partner_shipping_id = line.sale_id.partner_shipping_id \
                if line.sale_id and line.sale_id.partner_shipping_id else ''

    @api.onchange('repair_id')
    def onchange_repair_id(self):
        for line in self:
            line.partner_shipping_id = line.repair_id.address_id \
                if line.repair_id and line.repair_id.address_id else ''

    @api.onchange('purchase_id')
    def onchange_purchase(self):
        for line in self:
            line.partner_shipping_id = line.purchase_id.partner_id \
                if line.purchase_id and line.purchase_id.partner_id else ''

    @api.model
    def default_get(self, fields):
        res = super(AddShippingSPOL, self).default_get(fields)
        active_id = self._context.get('active_id')
        active_model = self._context.get('active_model', False)
        if not active_id or not active_model:
            raise ValidationError(_("Có lỗi xảy ra! \nVui lòng liên hệ Quản Lý của hệ thống để sửa lỗi."))
        if active_model and active_model != 'shipping.order':
            raise ValidationError(_("Chức năng này không được sử dụng cho đối tượng %s.") % active_model)
        spo_id = self.env[active_model].browse(active_id)
        if not spo_id:
            raise ValidationError(_("Không tìm thấy Phiếu giao hàng để áp dụng."))
        res['spo_id'] = spo_id.id
        spls = sorted(spo_id.sp_line_ids, key=lambda x: x['sequence'], reverse=True)
        if spls:
            res['partner_source_id'] = spls[0].partner_shipping_id.id
        else:
            res['partner_source_id'] = spo_id.partner_source_id.id
        return res

    def action_add_shipping_line(self):
        if not self.spo_id:
            raise ValidationError(_("Không tìm thấy Phiếu giao hàng để áp dụng."))
        self.spo_id.write({'sp_line_ids': [(0, 0, {
            'partner_source_id': self.partner_source_id.id,
            'from_address': self.from_address,
            'order_type': self.order_type,
            'sale_id': self.sale_id.id if self.sale_id else False,
            'repair_id': self.repair_id.id if self.repair_id else False,
            'purchase_id': self.purchase_id.id if self.purchase_id else False,
            'partner_shipping_id': self.partner_shipping_id.id,
            'to_address': self.to_address,
            'phone': self.partner_shipping_id.phone or self.partner_shipping_id.mobile or '',
            'distance': self.distance,
            'extra_amount_id': self.extra_amount_id.id,
            'extra_amount': self.extra_amount,
            'spo_id': self.spo_id,
            'note': self.note,
        })]})
        return True
