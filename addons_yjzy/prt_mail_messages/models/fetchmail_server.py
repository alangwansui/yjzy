# -*- coding: utf-8 -*-



from odoo import api, fields, models, tools, _

class fetchmail_server(models.Model):
    _inherit = 'fetchmail.server'

    @api.depends('user')
    def compute_partner(self):
        obj = self.env['res.partner']
        for one in self:
            one.partner_id = obj.search([('email', '=', one.user)], limit=1)

    partner_id = fields.Many2one('res.partner', u'相关的伙伴', compute=compute_partner,store=True)

    last_alias_id = fields.Many2one('mail.alias', '无匹配的别名')


    


