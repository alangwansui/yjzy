# -*- coding: utf-8 -*-
{
    'name': "picking_show_order_qty",

    'summary': """
        picking_show_order_qty""",

    'description': """
       picking_show_order_qty
    """,

    'author': "jon<alangwansui@qq.com>",
    'website': "www.yjzy.com",
    'category': 'xxxx',
    'version': '0.1',

    'depends': ['stock', 'sale', 'sale_stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/picking.xml',
    ],

    'demo': [
        #'demo/demo.xml',
    ],


    'price': 10,
    'currency': 'EUR',
    'installable': True,
    'application': True,
    'auto_install': False,
}