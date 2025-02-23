# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "DHL Shipping",
    'description': "Send your shippings through DHL and track them online",
    'category': 'Warehouse',
    'version': '1.0',
    'depends': ['delivery', 'mail'],
    'data': [
        'data/delivery_dhl_data.xml',
        'views/delivery_dhl_view.xml',
        'views/res_config_settings_views.xml',
    ],
    'license': 'OEEL-1',
}
