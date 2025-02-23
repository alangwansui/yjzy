from odoo import models, fields, api, _, tools, SUPERUSER_ID, registry
from odoo.tools.misc import split_every
import logging
from odoo.exceptions import MissingError, AccessError

_logger = logging.getLogger(__name__)



class res_users(models.Model):
    _inherit = "res.users"

    sup_message_uids = fields.Many2many('res.users', 'ref_message_user', 'sup_uid', 'sub_uid', '消息上级用户')
    sub_message_uids = fields.Many2many('res.users', 'ref_message_user', 'sub_uid', 'sup_uid', '消息下级用户')


    def open_message(self):
        self.ensure_one()
        #打开消息的过滤定义
        dm = [('owner_user_id', '=', self.id), ('message_type', '=', 'email'),('state_delete', '!=', 'recycle')]

        action = self.env.ref('prt_mail_messages.action_mail_messages_personal').read()[0]
        action['domain'] = dm

        return action

    ##[['|',
                  ##      ['all_user_ids', 'in', [treeNode.dbid]],
                  ##      ['all_user_ids.sup_message_uids', 'in', [treeNode.dbid]],
                   ##     ['state_delete', '!=', 'recycle'],
                    ##    ]]