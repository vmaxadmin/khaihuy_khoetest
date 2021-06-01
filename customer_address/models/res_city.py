from odoo import api, fields, models


class City(models.Model):
    _name = 'res.city'
    _description = 'Cities'

    name = fields.Char('Name')
    code = fields.Char('Code')
    country_id = fields.Many2one('res.country', 'Country')
