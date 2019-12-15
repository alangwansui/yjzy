# -*- coding: utf-8 -*-
{
    'name': "pricelist_auto_update",

    'summary': """
        pricelist_auto_update""",

    'description': """
        pricelist_auto_update
    """,

    'author': "jon<alangwansui@qq.com>",
    'website': "http://www.yourcompany.com",


    'category': 'sale',
    'version': '0.1',


    'depends': ['sale', 'product', 'purchase'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
    ],

    'demo': [
    ],

    'installable': True
}