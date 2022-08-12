# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError
from odoo.tools import ustr
import os
import base64
import tempfile,zipfile
from io import BytesIO
from PIL import Image
import io
import codecs


class sh_export_product_image_tmpl(models.TransientModel):
    _name = "sh.export.product.image.tmpl"
    _description = "Export Product Image Template"
    
    file_name = fields.Selection([
        ('barcode','Barcode'),
        ('default_code','Internal Reference'),
        ('name','Name'),
        ('id','ID'),
        ], string = "Image Name As", required = True, default = "name")
    
    product_tmpl_ids = fields.Many2many('product.template', string='Products', store=False)
        
    file = fields.Binary(string = "Zip")    
    zip_file_name = fields.Char(string = "File Name")
        
    @api.model
    def default_get(self, fields):
        rec = super(sh_export_product_image_tmpl, self).default_get(fields)
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')

        if not active_ids:
            raise UserError(_("Programming error: wizard action executed without active_ids in context."))
        
        if not active_ids or active_model != 'product.template':
            return rec        

        product_tmpls = self.env['product.template'].browse(active_ids)
        
        rec.update({
            'product_tmpl_ids':[(6, 0, product_tmpls.ids)],
            })
        return rec
    

    
    @api.multi
    def action_export(self):
        if self:            
            try:
                mem_zip = BytesIO()
                tmp_dir = tempfile.mkdtemp()
                with zipfile.ZipFile(mem_zip, mode="w",compression=zipfile.ZIP_DEFLATED) as zf:            
                    for product in self.product_tmpl_ids:
                        
                        # ====================================================
                        # Define a product name
                        # ====================================================                           
                        name_product = product.name
                        if self.file_name == 'barcode' and product.barcode:
                            name_product = product.barcode
                        elif self.file_name == 'default_code' and product.default_code:
                            name_product = product.default_code                            
                        elif self.file_name == 'id':
                            name_product = str(product.id)                               
                        
                        # ====================================================
                        # take image from product field and write it into zip.
                        # ====================================================                        
                        if product.image:
                            im = Image.open(BytesIO(base64.b64decode(product.image)))                    
                            imgext = '.' + Image.MIME[im.format].split('/')[1]                                        
                            file_path = os.path.join( tmp_dir, name_product + imgext) 
                            im.save( file_path)                     
                            zf.write(file_path)               
                           
                # ====================================================
                # assign image to wizard field.
                # ====================================================                 
                self.file = base64.encodestring(mem_zip.getvalue())  
                self.zip_file_name = 'product_images.zip'                 
            
            except Exception as e:
                raise UserError(_("Something went wrong! " + ustr(e) ))                
                          
            
            # ====================================================
            # Return self object of wizard.
            # ====================================================               
            return {
                    'name' : 'Export Images',
                    'view_mode': 'form',
                    'res_id': self.id,
                    'res_model': 'sh.export.product.image.tmpl',
                    'view_type': 'form',
                    'type': 'ir.actions.act_window',
                    'context': self.env.context,
                    'target': 'new',
                       }                             
