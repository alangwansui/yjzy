# -*- coding: utf-8 -*-
{
    'name': 'X2M Select and Delete Multiple Records',
    'summary': 'X2M Select and Delete Multiple Records in Odoo',
    'author': "Crest Infosys",
    # 'website': "http://www.crestinfosys.com",
    'license': 'OPL-1',
    'version': '11.0.1.0',
    'description': """
        This module enable you to select and delete multiple records from X2M field in odoo.
    """,
    'category': 'Tools',
    'depends': ['web'],
    'data': [
        'views/x2m_multi_delete_templates.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'price': 15.0,
    'currency': 'EUR',
    'installable': True,
    'application': True,
    'auto_install': False
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
