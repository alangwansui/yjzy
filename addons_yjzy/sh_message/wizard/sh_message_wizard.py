# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import api, fields, models, _

class sh_message_wizard(models.TransientModel):
    _name="sh.message.wizard"
    
    def get_default(self):
        if self.env.context.get("message",False):
            return self.env.context.get("message")
        return False 

    name=fields.Text(string="Message",readonly=True,default=get_default)

    def apply(self):
        res_model = self.env.context.get('res_model')
        res_id = self.env.context.get('res_id')
        views = self.env.context.get('views')
        return{
            'name': 'test',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': res_model,
            'res_id': res_id,
            'views': [(views, 'form')],
            # 'target': 'new',

            'type': 'ir.actions.act_window',
            'context': {},

        }

    