# © 2018-Today Aktiv Software (http://www.aktivsoftware.com).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': "Reset Delivery Order",

    'summary': """
        You can reset the delivery order.""",
    'description': """
        You can only reset the delivery order from
        sales which have not been cancelled.
    """,
    'author': "Aktiv Software",
    'license': "AGPL-3",
    'website': "http://www.aktivsoftware.com",
    'category': 'Sale',
    'version': '11.0.1.0.0',
    'images': ['static/description/banner.jpg'],
    'depends': ['sale_management', 'stock'],
    'data': [
        'views/stock_picking_view.xml',
    ],
}
