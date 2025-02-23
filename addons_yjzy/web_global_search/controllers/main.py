# -*- coding: utf-8 -*-

import odoo
from odoo import http
from odoo.addons.web.controllers.main import *
from odoo.http import request
import numbers


class GlobalSearch(http.Controller):

    @http.route('/globalsearch/model_fields', type='json', auth="public")
    def search_model_fields(self, **kwargs):
        global_search_config = request.env['global.search.config'].sudo().search([('user_id', '=', request.env.user.id)])
        result = dict([(gs.model_id.name, gs.model_id.model) for gs in global_search_config if len(gs.field_ids) > 0])
        return result

    @http.route('/globalsearch/search_data', type='json', auth="public")
    def search_data(self, **kwargs):
        search_string = kwargs['search_string']
        global_search_config = request.env['global.search.config'].sudo().search([('user_id', '=', request.env.user.id), ('model_id.model', '=', kwargs['model'])], limit=1)
        if len(global_search_config.field_ids) > 0:
            fields = dict([(field.name, (field.field_description, field.relation)) for field in global_search_config.field_ids])
            dom = ['|' for l in range(len(fields)-1)]
            dom.extend([(f, 'ilike', kwargs['search_string']) for f in fields.keys()])
            datas = request.env[kwargs['model']].search_read(dom, list(fields.keys()) + ['display_name'])
            for data in datas:
                for f,v in list(data.items()):
                    if f in ['display_name', 'id']:
                        continue
                    if type(v) is list:
                        if data[f]:
                            x2m_data = request.env[fields[f][1]].browse(data[f]).name_get()
                            x2m_v = ', '.join([d[1] for d in x2m_data if search_string.lower() in d[1].lower()])
                            if x2m_v:
                                data[fields[f][0]] = x2m_v
                    elif type(v) is tuple:
                        if data[f] and data[f][1] and search_string.lower() in data[f][1].lower():
                            data[fields[f][0]] = data[f][1]
                    else:
                        if isinstance(data[f], numbers.Number) and type(data[f]) is not bool:
                            data[f] = str(data[f])
                        if data[f] and search_string.lower() in data[f].lower():
                            data[fields[f][0]] = data[f]
                    del data[f]
                    if data.get(fields[f][0]) and kwargs['search_string'].lower() not in data[fields[f][0]].lower():
                        del data[fields[f][0]]
                data['model'] = kwargs['model']
            return datas or [{'label': '(no result)'}]
        return [{'label': '(no result)'}]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
