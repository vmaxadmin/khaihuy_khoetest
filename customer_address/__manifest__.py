# -*- coding: utf-8 -*-
##############################################################################
{
    'name': 'Customer Address Information',
    'version': '1.0',
    'category': 'base',
    'author': 'AlvinY',
    'license': 'AGPL-3',
    'website': '',
    'description': """
        Module to customize Customer for adding more information:
        Address in Vietnam
    """,
    'depends': [
        # Odoo SA
        'base',
    ],
    'data': [
        # Data
        'data/res.city.csv',
        'data/res.district.csv',
        'data/res.ward.csv',
        # View
        'views/res_bank.xml',
        'views/res_city.xml',
        'views/res_company.xml',
        'views/res_district.xml',
        'views/res_partner.xml',
        'views/res_ward.xml',
        # Menu
        'menu/menu.xml',
        # Security
        'security/ir.model.access.csv',
    ],
    'qweb': [],
    'demo': [],
    'installable': True,
    'application': True,
    'sequence': 3
}
