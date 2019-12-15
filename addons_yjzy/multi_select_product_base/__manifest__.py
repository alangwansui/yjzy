# -*- coding: utf-8 -*-
{
    'name': u"multi select_product_base,产品多选基础",

    'summary': """
     """,

    'description': """
        The base model for easy to add lines record includ product 
    """,

    'author': "jon<alangwansui@qq.com>",
    'website': "",

    'category': 'tools',
    'version': '0.1',

    'depends': ['product', 'stock'],

    'data': [
        # 'security/ir.model.access.csv',
        'views/product.xml',
    ],

    'demo': [
    ],

    'images': [
        #'static/description/theme.jpg',
    ],

    'qweb':[
        ##'static/src/xml/template.xml',
    ],

    'auto_install': False,
    'installable': True,
    'active': True,
    'currency': 'EUR',
    'price': 1,

}