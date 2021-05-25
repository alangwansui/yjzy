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

        'data/res_groups.xml',
        'views/bank_reconciliation.xml',




        'template/no_header_external_layout.xml',
        'security/ir.model.access.csv',
        'security/yjzy_extend_security.xml',

        'views/hs.xml',
        'views/company.xml',
        'views/user.xml',

        'views/account_account.xml',
        'views/account_payment.xml',
        #'views/account_payment2.xml',
        #'views/account_payment3.xml',
        'wizard/transport_refuse_reason_views.xml',
        'wizard/account_invoice_refuse_reason_views.xml',
        'wizard/so_refuse_reason_views.xml',
        'wizard/po_refuse_reason_views.xml',
        'wizard/hxd_refuse_reason_views.xml',
        'wizard/payment_refuse_reason_views.xml',
        'wizard/expense_sheet_refuse_reason_views.xml',
        'wizard/account_reconcile_refuse_reason_views.xml',
        'wizard/tb_po_invoice_refuse_reason_views.xml',
        'wizard/wizard_renling.xml',
        'wizard/wizard_multi_sale_line.xml',
        'wizard/wizard_fkzl.xml',
        'wizard/wizard_renling_ysrld.xml',
        'wizard/wizard_tb_po_invoice_with_out_tax.xml',
        'wizard/wizard_plan_check_comments.xml',
        'wizard/back_tax_refuse_reason_views.xml',
        'wizard/wizard_tb_po_invoice_new.xml',

        'views/account_invoice_extra.xml',
        'views/account_journal.xml',
        'views/account_move.xml',
        'views/account_invoice_new_in_one.xml',
        'views/account_invoice.xml',
        'views/account_invoice_new.xml',


        'views/account_reconcile_orde.xml',
        'views/account_reconcile_orde2.xml',
        #'views/account_reconcile_orde3.xml',
        'views/bom_template.xml',
        'views/misc.xml',
        'views/partner.xml',
        'views/partner_new.xml',
        'views/product_template.xml',
        'views/product_product.xml',

        'views/product_category.xml',
        'views/product_attribute.xml',
        'views/product_supplierinfo.xml',
        'views/usd_pool.xml',
        'views/transport_bill_usd_pool.xml',
        'views/transport_bill_declare_po.xml',
        'views/account_journal_dashboard_view.xml',


        'views/sale.xml',
        'views/sale2.xml',
        'views/sale3.xml',
        'views/sale4.xml',
        'views/sales_cost_1.xml',
        'views/purchase.xml',
        'views/purchase2.xml',
        # 'views/sale_cost.xml',
        'views/stock.xml',
        'views/transport_bill.xml',
        'views/transport_bill_account.xml',
        'views/transport_bill_new.xml',
        'views/transport_bill_tenyale.xml',
        'views/transport_bill_customs_clearance.xml',
        'views/transport_bill_customs_declare.xml',
        'views/transport_bill_supplier_delivery.xml',
        'views/transport_bill_date.xml',
        'views/transport_bill_wkf.xml',
        'views/transport_lot_plan.xml',
        'views/transport_bill_vendor.xml',
        'views/transport_bill_line_tenyale.xml',
        'views/trans_date_attachment.xml',
        'views/account_invoice_stage.xml',
        'views/hr_expense_stage.xml',
        'views/sale_order_line.xml',
        'views/account_invoice_rzhi.xml',

        'views/product_packaging.xml',

        'views/config_setting.xml',
        'views/hr_expense.xml',
        'views/hr_expense_new.xml',
        'views/bom.xml',
        'views/bank.xml',
        'views/ir_translation.xml',
        'views/mail.xml',
        'views/budget_budget.xml',
        'views/gongsi.xml',
        'views/jituan.xml',
        'views/pricelist.xml',
        'views/product_partner_origin.xml',
        'views/print_record.xml',
        'views/partner_level.xml',
        'views/partner_source.xml',
        'views/product_product_new.xml',
        'views/dashboard.xml',
        'views/transport_bill_customs_invoice.xml',
        'views/order_track_att.xml',


        'views/trasnport_bill_stage.xml',
        'views/sale_stage.xml',
        'views/purchase_stage.xml',
        'views/account_invoice_extra_po.xml',
        'views/tb_po_invoice_other.xml',
        'views/tb_po_invoice.xml',
        'views/mail_activity_views.xml',
        'views/plan_check.xml',

        'views/hr_expense_other_payment.xml',
        'views/account_bank_statement_1.xml',
        'views/real_invoice.xml',

        'views/menu.xml',



        'views2/plan_invoice_auto.xml',
        'views2/real_invoice_auto.xml',
        'views2/transport_bill_account.xml',
        'views2/ysrld_new.xml',
        'views2/rcskd.xml',
        'views2/rcskd_new.xml',
        'views2/rcfkd.xml',
        'views2/ysrld.xml',
        'views2/yfsqd.xml',
        'views2/rcfksqd.xml',
        'views2/rcskd_fkzl.xml',
        'views2/rcskrld.xml',
        'views2/yshxd.xml',
        'views2/yshxd_new.xml',
        'views2/yfhxd.xml',
        'views2/yfhxd_new.xml',
        'views2/nbzz.xml',
        'views2/jiehui.xml',
        'views2/account_reconcile_stage.xml',
        'views2/account_payment_reconcile.xml',



        'views2/expense.xml',
        'views2/expense_sheet.xml',
        'views2/fkzl.xml',
        'views2/rcfkd_fksq.xml',
        'views2/account_move_line_bank.xml',
        'views2/menu.xml',

        'views/back_tax_declaration.xml',

        'data/data.xml',
        'data/message_subtype.xml',
        'data/sequence_sfk.xml',
        'data/cron.xml',
        'data/stage_data.xml',
        'data/message_data.xml',
        'data/plan_automation_data.xml',


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
        'wizard/wizard_batch_passwd.xml',
        'wizard/wizard_so2sol.xml',
        'wizard/wizard_tb_po_invoice.xml',
        'wizard/wizard_reconcile_invoice.xml',
        'wizard/wizard_back_tax_declaration_line.xml',
        'wizard/wizard_create_other.xml',
        'wizard/wizard_print_fkzl.xml',
        'wizard/purchase_payment_advance_tool.xml',

        # report
        'report/report.xml',
        'report/sale_contract_template.xml',
        'report/sale_contract2_template.xml',

        'report/transport_bill_invoice_template.xml',
        'report/transport_bill_packing_template.xml',
        'report/report_transport_bill_action.xml',
        'report/transport_bill_fytzd_template.xml',
        'report/transport_bill_bgzl_contract_template.xml',
        'report/transport_bill_bgzl_invoice_template.xml',
        'report/transport_bill_bgzl_purchase_template.xml',
        'report/transport_bill_bgzl_packing_template.xml',
        'report/transport_bill_bgzl_bgd_template.xml',
        'report/transport_bill_vendor_template.xml',
        'report/purchase_contract_template.xml',
        'report/purchase_contract2_template.xml',
        'report/report_partner_customer_template.xml',
        'report/report_partner_paymnent_template.xml',
        'report/report_partner_invoice_paymnent_template.xml',


        'report/sale_order_cost_template.xml',

        'report/account_payment_ysrld_liushui_template.xml',
        'report/account_payment_yfrld_liushui_template.xml',
        'report/report_transport_bill_test_template.xml',
        'report/report_partner_invoice_template.xml',
        'report/report_fkzl_template.xml',

        'template/assets.xml',


    ],

    'qweb': [
        "static/src/xml/template.xml",
        "static/src/xml/activity.xml",
    ],

    'pre_init_hook': 'pre_init_hook',

}
