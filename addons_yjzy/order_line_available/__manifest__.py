# -*- coding: utf-8 -*-
{
    'name': "order_line_available",

    'summary': """
        order_line_available""",

    'description': """
       order_line_available
    """,

    'author': "jon<alangwansui@qq.com>",
    'website': "www.yjzy.com",
    'category': 'xxxx',
    'version': '0.1',

    'depends': ['sale', 'purchase', 'stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
    ],



    'price': 10,
    'currency': 'EUR',
    'installable': True,
    'application': True,
    'auto_install': False,
}