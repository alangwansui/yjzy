# -*- coding: utf-8 -*-
{
    'name': "yjzy_extend",

    'summary': """
        yjzy_extend""",

    'description': """
       yjzy_extend
    """,

    'author': "jon<alangwansui@qq.com>",
    'website': "http://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['stock', 'sale', 'purchase', 'sale_stock',
                'purchase_order_product_name_last_price',
                'sale_order_product_name_last_price', 'delivery',
                'multi_select_product_purchase', 'multi_select_product_sale', 'multi_select_product_picking',
                'lot_price', 'lot_usage_model', 'purchase_sale_reserved', 'order_line_available',
                'account', 'account_tax_code', 'mrp', 'account_payment_advance',
                'wkf_powerful', 'delivery_status', 'sale_order_dates', 'oh_employee_creation_from_user',
                'mrp', 'product_category_code', 'website_sale', 'hr_expense',
                ],

    'data': [

        'views/menu.xml',

        'template/no_header_external_layout.xml',
        'security/ir.model.access.csv',

        'views/hs.xml',
        'views/company.xml',
        'views/user.xml',

        'views/account_account.xml',
        'views/account_payment.xml',
        #'views/account_payment2.xml',
        #'views/account_payment3.xml',

        'views/account_move.xml',
        'views/account_invoice.xml',
        'views/account_reconcile_orde.xml',
        'views/account_reconcile_orde2.xml',
        'views/bom_template.xml',
        'views/misc.xml',
        'views/partner.xml',

        'views/product_template.xml',
        'views/product_product.xml',

        'views/product_category.xml',
        'views/product_attribute.xml',
        'views/product_supplierinfo.xml',

        'views/sale.xml',
        'views/sale2.xml',
        'views/purchase.xml',
        # 'views/sale_cost.xml',
        'views/stock.xml',
        'views/transport_bill.xml',
        'views/transport_bill_account.xml',
        'views/transport_lot_plan.xml',
        'views/transport_bill_vendor.xml',

        'views/product_packaging.xml',
        'views/config_setting.xml',
        'views/hr_expense.xml',
        'views/bom.xml',
        'views/bank.xml',
        'views/ir_translation.xml',
        'views/mail.xml',


        'views2/menu.xml',
        'views2/rcskd.xml',
        'views2/rcfkd.xml',
        'views2/ysrld.xml',
        'views2/yfsqd.xml',
        'views2/rcfksqd.xml',
        'views2/rcskrld.xml',
        'views2/yshxd.xml',
        'views2/yfhxd.xml',
        'views2/nbzz.xml',
        'views2/jiehui.xml',

        'views2/expense.xml',
        'views2/expense_sheet.xml',


        'data/data.xml',
        'data/message_subtype.xml',
        'data/sequence_sfk.xml',
        'data/cron.xml',

        # 'wizard/wizard_so2po.xml',
        'wizard/wizard_transport4so.xml',
        'wizard/wizard_attribute_configurator.xml',
        'wizard/wizard_transport_lot_plan.xml',
        'wizard/wizard_tb2tb_account.xml',
        'wizard/wizard_product_copy.xml',
        'wizard/wizard_bom_template.xml',
        'wizard/wizard_po_box.xml',
        'wizard/wizard_bom_sale.xml',
        'wizard/wizard_supplier_invoice_date.xml',

        # report
        'report/report.xml',
        'report/sale_contract_template.xml',
        'report/sale_contract2_template.xml',

        'report/transport_bill_invoice_template.xml',
        'report/transport_bill_packing_template.xml',
        'report/transport_bill_fytzd_template.xml',
        'report/transport_bill_bgzl_contract_template.xml',
        'report/transport_bill_bgzl_invoice_template.xml',
        'report/transport_bill_bgzl_purchase_template.xml',
        'report/transport_bill_bgzl_packing_template.xml',
        'report/transport_bill_bgzl_bgd_template.xml',
        'report/transport_bill_vendor_template.xml',
        'report/purchase_contract_template.xml',
        'report/purchase_contract2_template.xml',

        'report/sale_order_cost_template.xml',

        'report/account_payment_ysrld_liushui_template.xml',
        'report/account_payment_yfrld_liushui_template.xml',


    ],

    'qweb': [
        "static/src/xml/template.xml",
    ],

    'pre_init_hook': 'pre_init_hook',

}
