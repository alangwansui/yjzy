# -*- coding: utf-8 -*-
{
    'name': "excel_text_parser",

    'summary': """
        excel_text_parser""",

    'description': """
       excel 复制文本解析
       1: 需要的模型上可以直接添加  open_excel_text_parser  方法调用向导,粘贴复制的excel文本后,点击确定 解析返回一个 二维数组.
       2: 模型需要定义一个名为 process_excel_text 的方法,处理得到的二位数组.
    """,

    'category': 'Tools',
    'version': '0.1',

    'depends': ['base', 'sale'],

    'data': [
        'views/excel_text_parser.xml',

    ]
}
