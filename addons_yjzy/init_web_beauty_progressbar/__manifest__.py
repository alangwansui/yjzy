{
    'name': 'INIT - Beauty Progressbar',
    'version': '11.0.1.0.1',
    'category': 'Extra Tools',
    'summary': 'Beauty Progressbar',
    'author': 'Init Co. Ltd',
    'support': 'minhnq@init.vn',
    'website': 'https://init.vn',
    'license': 'LGPL-3',
    'description': """
Show percent value in Progress Bar
=====================================================================================================================
Make progressbar more beautiful and show percent number in Progressbar 

        """,
    'depends': ['web'],
    'data': [
        'view/template.xml',
    ],
    'qweb': [
        'static/src/xml/percent_progressbar_template.xml'
    ],
    'demo': [],
    'test': [],
    'images': ['static/description/banner.png'],
    'bootstrap': True,
    'installable': True,
}
