# -*- coding: utf-8 -*-
{
    'name': u"multi select product for purchase order,采购产品多选",

    'summary': """
        easy to add multi product for PO
     """,

    'description': """
        easy to add multi product for PO
    """,

    'author': "jon<alangwansui@qq.com>",
    'website': "",

    'category': 'purchase',
    'version': '0.1',

    'depends': ['multi_select_product_base', 'purchase'],

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