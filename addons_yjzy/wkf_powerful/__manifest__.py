# -*- coding: utf-8 -*-
##############################################################################
{
    "name": "Powerfull Custom Workflow,",
    "version": "1.0",
    "website": "http://odoo.picp.net:10652",
    "depends": ["base","web", "purchase", "calendar"],
    "author": "<Jon alangwansui@qq.com>",
    "category": "Tools",
    "description": """
       An Powerfull Custom Workflow Tool. Very easy to create and update Workflow!
    """,
    "data": [
        'secureity/ir.model.access.csv',
        'views/wkf.xml',
        'wizard/wizard_wkf.xml',

        'views/template.xml',

    ],

    'demo':[
        'demo/wkf.base.csv',
        'demo/wkf.node.csv',
        'demo/wkf.trans.csv',
    ],
    #'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'active': True,
    'price': 500,
    'currency': 'EUR',
    'auto_install': True,


}