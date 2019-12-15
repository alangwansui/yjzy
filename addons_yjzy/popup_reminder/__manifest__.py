# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.
{
    'name': 'Pop-up Reminder 11.0',
    'version': '11.0.1.0.0',
    'category': 'Base',
    'summary': 'Popup Reminder',
    'description': """
Automatic Reminder System
=========================

This module will provide generalised feature to configure various reminders on
different models.

You can configure reminders on any parameter and set for the current month,
today, next month, and daily basis.

This module will help you to get reminders for :

* Employee's passport expiring next month
* Visa expiring on next month
* List of tasks having deadlines today
* List of tasks to be start today
* List of leads and opportunities having action date today
    """,
    'author': 'Serpent Consulting Services Pvt. Ltd.',
    'website': 'http://www.serpentcs.com',
    'depends': ['base', 'web', 'bus'],
    'data': [
        'security/ir.model.access.csv',
        'views/popup_reminder_view.xml',
        'views/popup_views.xml'
    ],
    'qweb': ['static/src/xml/view.xml'],
    'images': ['static/description/Pop-upReminder.png'],
    'auto_install': False,
    'installable': True,
    'application': True,
    'price': 45,
    'currency': 'EUR',
}
