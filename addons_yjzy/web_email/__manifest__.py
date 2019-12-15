# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
{
    'name': 'Odoo as Inbox - Email Interface',
    'version': '11.0.1.0.0',
    'category': 'Extra Tools',
    'license': 'AGPL-3',
    'description': '''This module provides email interface for gmail accounts.
        Web Email
        Web Email Interface''',
    'summary': '''This module provides email interface for gmail accounts.
        Web Email
        Web Email Interface''',
    'author': 'Serpent Consulting Services Pvt. Ltd.',
    'website': 'http://www.serpentcs.com',
    'depends': ['web', 'website', 'mail', 'web_editor', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'security/emails_security.xml',
        'views/res_data.xml',
        'data/data.xml',
        'views/res_users.xml',
        'views/res_partner.xml',
        'views/layout.xml',
        'views/template.xml',
    ],
    'images': ['static/description/webemail_banner.jpg'],
    'application': True,
    'auto_install': False,
    'price': 399,
    'currency': 'EUR',
}