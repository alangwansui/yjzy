# -*- coding: utf-8 -*-
{
    'name': u"multi select product sale,销售产品多选",

    'summary': """
     """,

    'description': """
        multi select product for sale order
    """,

    'author': "jon<alangwansui@qq.com>",
    'website': "",

    'category': 'sale',
    'version': '0.1',

    'depends': ['multi_select_product_base', 'sale'],

    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
    ],

    'demo': [
    ],

    'images': [
        #'static/description/theme.jpg',
    ],

    'auto_install': False,
    'installable': True,
    'active': True,
    'currency': 'EUR',
    'price': 30,

}