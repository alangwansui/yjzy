# -*- coding: utf-8 -*-

{
    'name': 'Odoo Backend Automatic Logout',
    'version': '1.0',
    'category': 'All',
    'sequence': 6,
    'author': 'ErpMstar Solutions',
    'summary': 'Allows you to automatically logout when you do not interact with odoo.',
    'depends': ['web'],
    'data': [
        # 'security/ir.model.access.csv',
        'views/view.xml',
        # 'views/templates.xml',
    ],
    'qweb': [
        # 'static/src/xml/pos.xml',
    ],
    'images': [
        'static/description/logout.jpg',
    ],
    'installable': True,
    'website': '',
    'auto_install': False,
    'price': 25,
    'currency': 'EUR',
    'bootstrap': True,
}
