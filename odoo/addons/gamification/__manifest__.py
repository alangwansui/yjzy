# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Gamification',
    'version': '1.0',
    'sequence': 160,
    'category': 'Human Resources',
    'website' : 'https://www.odoo.com/page/gamification',
    'depends': ['mail', 'web_kanban_gauge'],
    'description': """
""",

    'data': [
        'wizard/update_goal.xml',
        'wizard/grant_badge.xml',
        'views/badge.xml',
        'views/challenge.xml',
        'views/goal.xml',
        'data/cron.xml',
        'security/gamification_security.xml',
        'security/ir.model.access.csv',
        'data/goal_base.xml',
        'data/badge.xml',
        'views/gamification.xml',
    ],
}
