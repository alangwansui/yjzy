# -*- coding: utf-8 -*-
{
    'name': u"multi_select_product_picking，调拨产品多选",

    'summary': """
     """,

    'description': """
        multi select product for picking order
    """,

    'author': "jon<alangwansui@qq.com>",
    'website': "",

    'category': 'warhouse',
    'version': '0.1',

    'depends': ['multi_select_product_base','stock'],

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