# -*- coding: utf-8 -*-
{
    'name': "product_dimension",

    'summary': """
        product_dimension""",

    'description': """
       product_dimension
    """,

    'author': "jon<alangwansui@qq.com>",
    'website': "www.yjzy.com",
    'category': 'xxxx',
    'version': '0.1',

    'depends': ['product', 'stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
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