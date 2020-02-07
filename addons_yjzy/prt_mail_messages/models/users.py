from odoo import models, fields, api, _, tools, SUPERUSER_ID, registry
from odoo.tools.misc import split_every
import logging
from odoo.exceptions import MissingError, AccessError

_logger = logging.getLogger(__name__)



class res_users(models.Model):
    _inherit = "res.users"

    sup_message_uids = fields.Many2many('res.users', 'ref_message_user', 'sup_uid', 'sub_uid', '消息上级用户')
    sub_message_uids = fields.Many2many('res.users', 'ref_message_user', 'sub_uid', 'sup_uid', '消息下级用户')


