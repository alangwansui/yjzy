# -*- coding: utf-8 -*-
from pprint import pprint as pp
from odoo import fields, api, models, SUPERUSER_ID
from odoo.models import BaseModel
from lxml import etree
import json
import logging

_logger = logging.getLogger(__name__)

old_fields_view_get = BaseModel.fields_view_get


def parse_search(self, res, view_type, dyn_view):
    _logger.info('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> parse_search >>')
    tree = etree.fromstring(res['arch'].decode('UTF-8'))
    for line in dyn_view.line_ids3:
        tmpl = '''<filter string="%s" domain = "[]" context="{'group_by':'%s'}"/>'''
        f_name = line.field_id.name
        f_str = res['fields'].get(f_name, {}).get('string') or f_name
        new_tag = etree.fromstring(tmpl % (f_str, f_name))
        for tag_position in tree.xpath('//group[@expand="0"]'):
            tag_position.append(new_tag)
    res['arch'] = etree.tostring(tree)
    return res


def parse_form(self, res, view_type, dyn_view):
    tree = etree.fromstring(res['arch'])
    invisible_key = 'invisible'

    _logger.info('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> parse_form >>')
    # modif field
    for line in dyn_view.line_ids:
        for tag in tree.xpath("//field[@name='%s']" % line.field_id.name):
            m_dic = json.loads(tag.get('modifiers', "{}"))
            # options = json.loads(tag.get('options', "{}"))
            options = eval(tag.get('options', "{}"))
            if line.invisible:
                tag.set('invisible', '1')
                m_dic.update({invisible_key: 1})
            if line.readonly:
                tag.set('readonly', '1')
                m_dic.update({'readonly': 1})
            if line.required:
                tag.set('required', '1')
                m_dic.update({'required': 1})
            if line.no_create:
                options.update({'no_create': True})
            if line.no_open:
                options.update({'no_open': True})
            new_m = json.dumps(m_dic)
            new_options = json.dumps(options)
            tag.set('modifiers', new_m)
            tag.set('options', new_options)
        # invisible label
        for tag in tree.xpath('//label[@for="%s"]' % line.field_id.name):
            if line.invisible:
                tag.getparent().remove(tag)

    # invisible button
    for line in dyn_view.button_ids:
        _logger.info('>>>>>>>>>button line %s' % line)
        for tag in tree.xpath("//button[@name='%s' or @string='%s']" % (line.name, line.name)):
            _logger.info('>>>>>>>>>button tag %s' % tag)
            if line.string:
                tag.set('string', line.string)
            if line.invisible:
                tag.set('style', "display:none;") #akiny取消
               # tag.set('invisible', 1)#akiny增加
                # tag.getparent().remove(tag)
            if line.hlight == 'yes':
                tag.set('class', 'oe_highlight')
            if line.hlight == 'no':
                tag.set('class', tag.get('class').replace('oe_highlight', ''))
            if line.confirm_text:
                tag.set('confirm', line.confirm_text)
            if line.group_ids:
                if self._uid != SUPERUSER_ID and not (set(self.env.user.groups_id) & set(line.group_ids)):
                    tag.set('style', "display:none;")
            if line.user_ids:
                user_ids_str = ','.join([str(x.id) for x in line.user_ids])
                tag.set('user_ids', user_ids_str)  #akiny
    # add field
    res['arch'] = etree.tostring(tree)
    return res


def parse_tree(self, res, view_type, dyn_view):
    _logger.info('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> parse_tree >>')
    tree = etree.fromstring(res['arch'])

    print ('？？？？？？？？', type(tree), type(res['arch']))
    for line in dyn_view.line_ids:
        for tag in tree.xpath("//field[@name='%s']" % line.field_id.name):
            m_dic = json.loads(tag.get('modifiers', "{}"))
            options = json.loads(tag.get('options', "{}"))
            if line.invisible:
                tag.set('invisible', '1')
                m_dic.update({'column_invisible': 1})
            if line.readonly:
                tag.set('readonly', '1')
                m_dic.update({'readonly': 1})
            if line.required:
                tag.set('required', '1')
                m_dic.update({'required': 1})
            if line.no_create:
                options.update({'no_create': True})
            if line.no_open:
                options.update({'no_open': True})
            new_m = json.dumps(m_dic)
            new_options = json.dumps(options)
            tag.set('modifiers', new_m)
            tag.set('options', new_options)

    # add field
    if dyn_view.type == 'tree':
        # _logger.info(res['arch'])
        for l in dyn_view.line_ids2:
            fname = l.field_id.name
            # update fields
            res['fields'].update(self.fields_get([fname]))
            e_field = etree.fromstring('<field name="%s"/>' % fname)

            if l.position in ['last', 'first']:
                tag_tree = tree.xpath("//tree")[0]
                if l.position == 'last':
                    tag_tree.append(e_field)
                else:
                    tag_tree.insert(0, e_field)

            elif l.position in ['after', 'before']:
                for tag_position in tree.xpath('//field[@name="%s"]' % l.position_field.name):
                    if l.position == 'after':
                        tag_position.addnext(e_field)
                    else:
                        tag_position.addprevious(e_field)
    print('>>>2', etree.tostring(tree))
    res['arch'] = etree.tostring(tree)
    return res


@api.model
def new_fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    res = old_fields_view_get(self, view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
    installed = 'dynamic_view' in self.env.registry._init_modules
    # print ">>>>>", installed, self.env.registry._init_modules
    # _logger.info(res['arch'])
    if installed:
        dyn_view_obj = self.env.get('dynamic.view')
        dynav = dyn_view_obj.search([('model_id.model', '=', res['model']), ('type', '=', res['type'])], limit=1)
        dynav_type = dynav.type
        if dynav:
            if view_type == dynav_type == 'tree':
                res = parse_tree(self, res, view_type, dynav)
            if view_type == dynav_type == 'form':
                res = parse_form(self, res, view_type, dynav)
            if view_type == dynav_type == 'search':
                res = parse_search(self, res, view_type, dynav)

    return res


BaseModel.fields_view_get = new_fields_view_get

#############################
