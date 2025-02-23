# -*- coding: utf-8 -*-
{
    'license': "OPL-1",
    'name': "Document Multi Download",
    'summary': "Support multiple file download form view",
    'author': "renjie <i@renjie.me>",
    'website': "https://renjie.me",
    'support': 'i@renjie.me',
    'category': 'Document Management',
    'version': '1.3',
    'price': 9.99,
    'currency': 'EUR',
    'depends': ['document'],
    'data': [
        'views/webclient_templates.xml',
    ],
    'qweb': [
        "static/src/xml/base.xml",
    ],
    'images': [
        'static/description/main_screenshot.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}