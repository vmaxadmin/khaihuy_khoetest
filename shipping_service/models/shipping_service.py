# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from . import googlemap_api
from odoo import api, models, fields, _
import requests

class ShippingService(models.Model):
    _name = 'shipping.service'
    _description = 'Shipping Service'

    name = fields.Char()
    free_over = fields.Boolean()
    amount_to_free = fields.Float()
    product_id = fields.Many2one('product.product', string='Delivery Product', required=True, ondelete='restrict')
    auto_add_fee = fields.Boolean('Auto Add Fee to Order')
    margin_percent = fields.Float(default=0)
    # Staff Shipping Service
    service_type = fields.Selection([('staff', 'Staff')], string='Service', default='staff', required=True)
    price_per_km = fields.Float()
    googlemaps_api_key = fields.Char()

    def compute_shipment_rate(self, ship):
        ''' Compute the price of the order shipment

        :param order: record of sale.order
        :return dict: {'success': boolean,
                       'price': a float,
                       'error_message': a string containing an error message,
                       'warning_message': a string containing a warning message}
                       # TODO maybe the currency code?
        '''
        self.ensure_one()
        if hasattr(self, '_compute_shipment_rate_%s' % self.service_type):
            res = getattr(self, '_compute_shipment_rate_%s' % self.service_type)(ship)
            return res

    def cancel_shipment(self, ship):
        self.ensure_one()
        if hasattr(self, '_cancel_shipment_%s' % self.service_type):
            getattr(self, '_cancel_shipment_%s' % self.service_type)(ship)
        # Executive if service is Staff
        else:
            if ship.state == 'done':
                raise UserError(_('You can not Cancel the Shipping Order is already Done !'))
            # elif ship.state == 'shipping' and self.env.user.id != ship.user_id.id:
            #     raise UserError(_('You can not Cancel the Shipping Order which you are not assigned to you !'))
            else:
                ship.write({'state': 'cancel'})

    def start_shipment(self, ship):
        self.ensure_one()
        if hasattr(self, '_start_shipment_%s' % self.service_type):
            getattr(self, '_start_shipment_%s' % self.service_type)(ship)
        # Executive if service is Staff
        else:
            if not ship.shipper_id:
                raise UserError(_('You must assign to a shipper before starting the shipment'))
            if ship.state != 'prepare':
                raise UserError(_('You can not start shipping order is in %s state') % ship.state)
            else:
                ship.write({'state': 'shipping'})

    def done_shipment(self, ship):
        self.ensure_one()
        if hasattr(self, '_done_shipment_%s' % self.service_type):
            getattr(self, '_done_shipment_%s' % self.service_type)(ship)
        # Executive if service is Staff
        else:
            if ship.state in ('cancel', 'prepare'):
                raise UserError(_('You can not done the shipping order in %s state') % ship.state)
            else:
                ship.write({'state': 'done',
                            'done_date': fields.Datetime.now()})

    def reset_to_draft(self, ship):
        self.ensure_one()
        if hasattr(self, '_reset_to_draft_%s' % self.service_type):
            getattr(self, '_reset_to_draft_%s' % self.service_type)(ship)
        else:
            if ship.state != 'cancel':
                raise UserError(_('You must cancel this shipment before reset to draft !'))
            else:
                ship.write({'state': 'prepare'})

    def get_shipment_status(self):
        pass

    def _get_label_template(self):
        pass

    def _send_shipping(self):
        pass

    def _compute_shipment_rate_staff(self, ship):
        def _get_source_address_staff(sh):
            # from_street = sh.partner_source_id.street or ''
            # from_ward = sh.partner_source_id.ward_id.name or ''
            # from_district = sh.partner_source_id.district_id.name or ''
            # from_city = sh.partner_source_id.city_id.name or ''
            # return ', '.join([el for el in [from_street, from_ward, from_district, from_city] if el != ''])
            return sh.partner_source_id.partner_address

        def _get_destination_address_staff(sh):
            # partner_shipping_id = sh.partner_shipping_id
            # to_street = partner_shipping_id.street or ''
            # to_ward = partner_shipping_id.ward_id.name or ''
            # to_district = partner_shipping_id.district_id.name or ''
            # to_city = partner_shipping_id.city_id.name or ''
            # return ', '.join([el for el in [to_street, to_ward, to_district, to_city] if el != ''])
            return sh.partner_shipping_id.partner_address
        # for sh_line in ship:
        source = _get_source_address_staff(ship)
        destination = _get_destination_address_staff(ship)
        api_key = self.googlemaps_api_key
        try:
            distance_m = googlemap_api.get_distance(source=source, destination=destination, api_key=api_key)
            distance_km = round((distance_m/1000)*2)/2
            price = ship.spo_id.service_id.price_per_km*distance_km
            return {'success': True,
                    'price': price,
                    'error_message': False,
                    'warning_message': False,
                    'distance': distance_km}
        except Exception as e:
            return {'success': False,
                    'price': 0,
                    'error_message': e,
                    'warning_message': False}
