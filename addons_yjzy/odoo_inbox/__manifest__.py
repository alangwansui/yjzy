# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Odoo Inbox',
    'category': 'Website',
    'author' : 'Kanak Infosystems LLP.',
    'version': '1.0',
    'description':
        """
Odoo Inbox
========================
        """,
    'depends': ['website', 'project', 'mail'],
    'auto_install': True,
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/template.xml',
        'views/mail_message.xml'
    ],
    'images': ['static/description/banner.jpg'],
    'installable': True,
    'license': 'OPL-1',
    'bootstrap': True,  # load translations for login screen
    'application': False,
    'price': 100,
    'currency': 'EUR',
}
