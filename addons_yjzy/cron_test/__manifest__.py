# -*- coding: utf-8 -*-
{
    'name': "cron_test",

    'summary': """
        cron_test""",

    'description': """
       cron_test
    """,

    'author': "jon<alangwansui@qq.com>",
    'website': "www.yjzy.com",
    'category': 'xxxx',
    'version': '0.1',

    'depends': ['base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'data/data.xml',
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