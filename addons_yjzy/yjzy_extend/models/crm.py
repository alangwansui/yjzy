# -*- coding: utf-8 -*-

from odoo import models, fields, api




class crm_lead(models.Model):
    _inherit = 'crm.lead'

    @api.model
    def create(self, vals):
        one = super(crm_lead, self).create(vals)
        budget = self.env['budget.budget'].create({
            'type': 'lead',
            'lead_id': one.id,
        })
        return one
