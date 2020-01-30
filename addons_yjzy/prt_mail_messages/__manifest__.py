# -*- coding: utf-8 -*-
{
    'name': 'Mail Messages Easy.'
            ' Reply to message, Forward messages or Move messages to other thread, Mark messages,'
            ' Email client style for messages views and more',
    'version': '11.0.4.0',
    'summary': """Read and manage all Odoo messages in one place!""",
    'author': 'Ivan Sokolov',
    'category': 'Sales',
    'license': 'GPL-3',
    'website': 'https://demo.cetmix.com',
    'description': """
Mail Messages
""",
    'depends': ['base', 'mail',],
    'live_test_url': 'https://demo.cetmix.com',
    'images': ['static/description/banner.png'],

    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',

        'views/menu.xml',
        'views/message.xml',
        'views/message_income.xml',
        'views/message_out.xml',

        'views/message_deleted.xml',
        'views/message_draft.xml',

        'views/personal_partner.xml',

        'views/partner.xml',
        'views/compose.xml',
        'views/mail_mail.xml',
        'views/fetchmail_server.xml',
        'views/mail_channel.xml',
        'template/assets.xml',
        'wizards/wizard_compose_action.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
