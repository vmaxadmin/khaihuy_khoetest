from odoo import api, fields, models, _
from odoo import exceptions


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ward_id = fields.Many2one('res.ward', 'Ward')
    district_id = fields.Many2one('res.district', 'District')
    city_id = fields.Many2one('res.city', 'City ID')
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict',
        default=lambda self: self.env.ref('base.vn'))
    partner_address = fields.Char('Address', compute='_compute_partner_address')

    def _compute_partner_address(self):
        for p in self:
            street = p.street or ''
            ward = p.ward_id.name or ''
            district = p.district_id.name or ''
            city = p.city_id.name or ''
            p.partner_address = ', '.join([el for el in [street, ward, district, city] if el != ''])
