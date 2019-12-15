# -*- coding: utf-8 -*-

{
    'name': 'WeChat Enterprise',
    'version': '1.0.0',
    'category': 'Social Network',
    'summary': '微信模块企业版扩展',
    'author': 'Oejia',
    'website': 'http://www.oejia.net/',
    'application': True,
    'data': [
        'data/oejia_wx.xml',
        'data/mail_shortcode_data.xml',
        'views/res_users_views.xml',
    ],
    'qweb': [
        'static/src/xml/oejia_wx.xml',
    ],
    'depends' : ['mail','oejia_wx'],
    'installable': True,
    'active': False,
    'web': True,
}
