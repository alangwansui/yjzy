# -*- coding: utf-8 -*-
##############################################################################
from odoo import api, fields, models, _
from odoo.models import BaseModel as BM
from odoo.exceptions import Warning
from odoo.tools.safe_eval import safe_eval
from odoo import fields, api, models, SUPERUSER_ID
from lxml import etree
import logging
_logger = logging.getLogger(__name__)

def str2tuple(s, self):
    return eval('tuple(%s)' % (s or ''))


## odoo.workflow.workitem.wkf_expr_eval_expr
def wkf_trans_condition_expr_eval(self, lines):
    result = False
    for line in lines.split('\n'):
        code = line.strip()
        if not code:
            continue
        if line == 'True':
            result = True
        elif line == 'False':
            result = False
        else:
            #self.model = self._name  # jon self.model is not def, from self._name
            #env = Environment(self._cr, self._uid, self._context)
            #ctx = self._context.copy()
            #result = safe_eval(line, mode="exec", nocopy=True)



            print ('===', code)

            result = eval(code)
    return result


# Set default state
default_get_old = BM.default_get


@api.model
def default_get_new(self, fields_list):
    res = default_get_old(self, fields_list)
    if 'x_wkf_state' in fields_list:
        res.update({'x_wkf_state': self.env['wkf.base'].get_default_state(self._name)})
    return res


@api.multi
def wkf_button_action(self):
    ctx = self.env.context.copy()
    _logger.info('wkf_button_action %s' % self.env.context)
    t_id = int(self.env.context.get('trans_id'))
    trans = self.env['wkf.trans'].browse(t_id)

    if trans.need_note:
        return {
            'name': _(u'工作流审批'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'wizard.wkf.message',
            'type': 'ir.actions.act_window',
            # 'view_id': False,
            'target': 'new',
            'context': ctx,
        }
    else:
        return self.wkf_action()


@api.multi
def wkf_clean_log(self):
    log_obj = self.env['log.wkf.trans']
    logs = log_obj.search([('res_id', '=', self.id)])
    logs.unlink()



@api.multi
def wkf_action(self, message=''):
    t_id = int(self.env.context.get('trans_id'))
    trans = self.env['wkf.trans'].browse(t_id)

    # condition_ok = eval(trans.condition)
    condition_ok = wkf_trans_condition_expr_eval(self, trans.condition)
    _logger.info('>>>>>>%s: %s', trans.condition, condition_ok)

    if not condition_ok:
        if trans.auto:
            _logger.info('condition false:%s', trans.condition)
            return True
        else:
            if self.env.context.get('no_pop'):
                return True
            else:
                raise Warning(u'Th condition is not allow to trans, Pleas contract with Administrator')

    # check repeat trans
    if not trans.is_backward:
        if self.env['log.wkf.trans'].search([('res_id', '=', self.id), ('trans_id', '=', t_id)], limit=1):
            raise Warning(_('The transfer had finish'))

    # check note
    # if trans.need_note and not self.x_wkf_note:
    #    raise Warning(_('The transfer can not empty note'))

    log = trans.make_log(self.name, self.id, message)
    # self.x_wkf_note = False

    # check  can be trans
    node_to = trans.node_to
    node_from = trans.node_from
    can_trans = node_to.check_trans_in(self.id)
    if can_trans:
        self.write({'x_wkf_state': str(node_to.id)})
        action, arg = node_to.action, node_to.arg
        action2, arg2 = node_to.action2, node_to.arg2
        action3, arg3 = node_to.action3, node_to.arg3

        # action
        if trans.is_backward:
            node_to.backward_cancel_logs(self.id)
        else:
            if action:
                _logger.info('======action:%s, arg:%s', action, arg)
                args = str2tuple(arg, self)
                getattr(self, action)(*args)

            if action2:
                _logger.info('======action2:%s, arg2:%s', action2, arg2)
                args2 = str2tuple(arg2, self)
                getattr(self, action2)(*args2)

            if action3:
                _logger.info('======action3:%s, arg3:%s', action3, arg3)
                args3 = str2tuple(arg3, self)
                getattr(self, action3)(*args3)

        # 2:event
        if node_to.event_need:
            my_name = self.name
            wizard_message = self.env.context.get('wizard_message', '')
            if wizard_message:
                my_name += ':%s' % wizard_message
            node_to.make_event(my_name,  self)

        # 3 auto trans
        auto_trains = filter(lambda t: t.auto, node_to.out_trans)
        for auto_t in auto_trains:
            self.with_context(trans_id=auto_t.id).wkf_button_action()

    return True


def wkf_button_show_log(self):
    return {
        'name': _('WorkFollow Logs'),
        'view_type': 'form',
        "view_mode": 'tree,form',
        'res_model': 'log.wkf.trans',
        'type': 'ir.actions.act_window',
        'view_id': False,
        'target': 'new',
        'domain': [('res_id', '=', self[0].id),('model','=', self._name)],
    }


def wkf_button_reset(self):
    logs = self.env['log.wkf.trans'].search([('res_id', '=', self[0].id), ('model', '=', self._name)])
    logs.write({'active': False})
    wkf_id = self.env.context.get('wkf_id')
    state = self.env['wkf.base'].browse(wkf_id).default_state
    self.write({'x_wkf_state': state})
    return True

    # default_x_state =



old_fields_view_get = BM.fields_view_get

@api.model
def new_fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    '''<button   user_ids="1,2,3" '''
    res = old_fields_view_get(self, view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
    view = etree.fromstring(res['arch'])
    for tag in view.xpath("//button[@user_ids]"):
        users_str = tag.get('user_ids')
        user_ids =[int(i) for i in  users_str.split(',')]
        if self._uid not in user_ids and self._uid != SUPERUSER_ID:
            tag.getparent().remove(tag)
    res['arch'] = etree.tostring(view)
    return res


BM.default_get = default_get_new
BM.wkf_button_action = wkf_button_action
BM.wkf_action = wkf_action
BM.wkf_button_show_log = wkf_button_show_log
BM.wkf_button_reset = wkf_button_reset
BM.wkf_clean_log = wkf_clean_log

BM.fields_view_get = new_fields_view_get
######################################################################






















##############################
