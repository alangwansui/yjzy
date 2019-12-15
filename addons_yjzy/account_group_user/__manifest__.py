# -*- coding: utf-8 -*-
# Copyright 2018 Jarvis (www.odoomod.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Account Group Accountant',
    "summary": "Account Group Accountant",
    "version": "1.0",
    "category": "Accounting",
    "website": "http://www.odoomod.com/",
    'description': """
Account Group Accountant
会计角色组
""",
    'author': "Jarvis (www.odoomod.com)",
    'website': 'http://www.odoomod.com',
    'license': 'AGPL-3',
    "depends": [
        'account',
    ],
    'external_dependencies': {
        'python': [],
        'bin': [],
    },
    "data": [
        'security/account_security.xml',
    ],
    'qweb': [
    ],
    'demo': [
    ],
    'css': [
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
