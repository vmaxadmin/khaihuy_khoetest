# -*- coding: utf-8 -*-

{
    'name' : 'Shipping Service',
    'version' : '1.1',
    'summary': 'Shipping Service',
    'description': """
====================
- Management shipping orders to customer
- Integration to third-party shipping service
    """,
    'category': '',
    'website': 'https://www.vmax.vn',
    'images' : [],
    'depends' : ['base', 'sales_team', 'sale', 'payment', 'repair'],
    'data': [
        # Security
        'security/security.xml',
        'security/ir.model.access.csv',
        # data
        'data/ir_sequence.xml',
        'data/shipment_serivce.xml',
        # Views
        'wizard/wizard_add_shipping_order_line.xml',
        'wizard/wizard_assign_order_to_shipping.xml',
        'views/shipping_order_views.xml',
        'views/sale_order_views.xml',
        'views/repair_order_views.xml',
        'views/shipping_service_views.xml',
        'views/shipping_extra_amount_views.xml',
        'views/purchase_order_views.xml',
        # Menu
        'menu/menu.xml',
    ],
    'demo': [
    ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
    'sequence': 4
}
