# -*- coding: utf-8 -*-
{
    'name': "manual_stock_reserved,移动数量手动控制预留",

    'summary': """
        manual_stock_reserved""",

    'description': """
       manual_stock_reserved，可以手动控制预留批次，预留数量，
    """,

    'author': "jon<alangwansui@qq.com>",
    'website': "www.yjzy.com",
    'category': 'xxxx',
    'version': '0.1',

    'depends': ['stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'wizard/wizard_manual_stock_reserve.xml',
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