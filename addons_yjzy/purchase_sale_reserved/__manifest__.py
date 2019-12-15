# -*- coding: utf-8 -*-
{
    'name': "purchase_sale_reserved",

    'summary': """
        purchase_sale_reserved""",

    'description': """
       purchase_sale_reserved
    """,

    'author': "jon<alangwansui@qq.com>",
    'website': "www.yjzy.com",
    'category': 'xxxx',
    'version': '0.1',

    'depends': ['stock', 'sale_stock', 'sale', 'purchase', 'manual_stock_reserve'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/lot.xml',
        'views/sale.xml',
        'views/stock.xml',
        'views/purchase.xml',
        'views/dummy_lot_reserve.xml',

        'wizard/wizard_so2po.xml',
        'wizard/wizard_sol_reserver.xml',
    ],

    'demo': [
        # 'demo/demo.xml',
    ],

    'price': 10,
    'currency': 'EUR',
    'installable': True,
    'application': True,
    'auto_install': False,
}
