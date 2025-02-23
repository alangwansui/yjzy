# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Deutschland - Accounting Reports',
    'version': '1.1',
    'category': 'Localization',
    'description': """
        Accounting reports for Deutschland
        Contains Balance sheet, Profit and Loss, VAT and Partner VAT reports
        Also add DATEV export options to general ledger
    """,
    'depends': [
        'l10n_de', 'account_reports'
    ],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_and_loss.xml',
        'data/tax_accounts.xml',
        'views/l10n_de_report_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}
