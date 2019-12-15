# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle 
#
##############################################################################
{
    'name': 'All in one Cancel Sale,Purchase,Picking', 
    'version': '11.0.1.0',
    'sequence': 1, 
    'category': 'Stock', 
    'summary': 'App will allow to cancel sale,purchase,picking,invoice in done state in single click',
    'description':  
        """ 
        App will allow to cancel sale,purchase,picking,invoice in done state in single click
        
        Tags:
        sale cancel, picking cancel, purchase cancel , cancel order, cancel shipment, cancel invoice, 
        Cancel sale order, cancel qutation, Cancel picking , cancel purchase order, cancel orders, cancel delivery order,
        cancel stock moves, cancel stock quants
 
    All in one Cancel Sale,Purchase,Picking
    Odoo cancel sale
    Odoo cancel purchase
    Odoo cancel picking
    Odoo All in one Cancel Sale,Purchase,Picking
    Cancel sale in odoo
    Cancel purchase in odoo
    Cancel picking in odoo
    odoo apps will help you to cancel sale order, purchase Order, picking, shipment and invoice after done state in odoo
    cancel sale, picking, purchase order into done state in odoo 
    Cancel button option in Picking,Sale, invoice , Purchase order in odoo
    cancel picking or sale order , relevant stock move will also canceled
    Cancel Stock Picking
    Cancel & Reset Picking
    Cancel Sales Order In Odoo
    Cancel purchase order in odoo
    Cancel Delivery Orders
    Stock Picking Cancel
        
        
    """,
    'depends': ['stock','sale_stock','account_cancel','purchase','sale'],
    "data": [
        "security/security.xml",
        "views/stock_view.xml",
    ],
    'demo': [],
    'test': [],
    'css': [],
    'qweb': [],
    'js': [],
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    
    #author and support Details
    'author': 'DevIntelle Consulting Service Pvt.Ltd',
    'website': 'http://www.devintellecs.com',    
    'maintainer': 'DevIntelle Consulting Service Pvt.Ltd', 
    'support': 'devintelle@gmail.com',
    'price':45.0,
    'currency':'EUR',
    'live_test_url':'https://youtu.be/Z8jMlB5ADNg',
}

