# -*- coding: utf-8 -*-
{
    'name': "multi_invoice_payment_extend",

    'summary': """
        multi_invoice_payment_extend""",

    'description': """
       multi_invoice_payment_extend
    """,

    'author': "jon<alangwansui@qq.com>",
    'website': "www.yjzy.com",
    'category': 'xxxx',
    'version': '0.1',

    'depends': ['account'],

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
    'installable': False,
    'application': False,
    'auto_install': False,
}