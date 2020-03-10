# -*- coding: utf-8 -*-
{
    'name': 'Advance Global Search',
    'summary': 'Search any records from odoo',
    'author': "Crest Infosys",
    # 'website': "http://www.crestinfosys.com",
    'license': 'OPL-1',
    'version': '11.0.1',
    'description': """
        This module enable you to global search feature, 
        you can search any records that you have access 
        and configured relavent models.
    """,
    'category': 'Tools',
    'depends': ['web'],
    'data': [
        'security/global_search_security.xml',
        'security/ir.model.access.csv',
        'views/search_config_view.xml',
        'views/global_search_template.xml',
    ],
    'qweb': [
        'static/src/xml/global_search.xml'
    ],
    'images': ['static/description/main_screenshot.png'],
    'price': 99.0,
    'currency': 'EUR',
    'installable': True,
    'application': True,
    'auto_install': False
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
