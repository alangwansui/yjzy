# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2018 Marlon Falcón Hernandez
#    (<http://www.falconsolutions.cl>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Delivery Status MFH',
    'version': '10.0.1.0.0',
    'author': 'Falcon Solutions SpA',
    'maintainer': 'Falcon Solutions SpA',
    'website': 'http://www.falconsolutions.cl',
    'license': 'AGPL-3',
    'category': 'delivery',
    'summary': 'Permite conocer el status de un envio',
    'description': """
Delivery Status
=====================================================
1-. Delivery Status in picking.\n
""",
    'depends': [
        'base', 'stock', 'sale', 'purchase',
    ],
    'data': [
        'views/stock_picking_view.xml',
        'views/sale_order_view.xml',
        'views/purchase_order_view.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,

}
