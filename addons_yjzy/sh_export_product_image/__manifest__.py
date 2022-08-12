# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name" : "Export Images in zip",
    "author" : "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Extra Tools",
    "summary": "Export Bulk of Images In zip, Export Mass Images Zip Module, Product Icons In Zip App,Export Several Pic In Zip, Export Bulk Photograph In Zip, Export Picture In Zip, Mass Image Export, Bulk Photos Export Odoo",
    "description": """This module will provide a feature to export product images in zip files on a single click.
 Export Bulk of Images In zip Odoo
 Export Mass Images In Zip Module, Put Product Icons In Zip,Export Several Pic In Zip, Export Bulk Photograph In Zip, Export Picture In Zip Odoo.
 Export Mass Images Zip Module, Product Icons In Zip App,Export Several Pic In Zip, Export Bulk Photograph In Zip, Export Picture In Zip Odoo.""",   
    "version":"10.0.2",
    "depends" : [
        
        "base",
        "sale",
        "product",
        
        ],
    "application" : True,
    "data" : [
        
        "security/export_product_img_security.xml",
        "wizard/product_var_multi_action.xml",
        "wizard/product_tmpl_multi_action.xml",
                    
            ],                         
    "images": ["static/description/background.png",],           
    "auto_install":False,
    "installable" : True,
    "price": 25,
    "currency": "EUR"   
}
