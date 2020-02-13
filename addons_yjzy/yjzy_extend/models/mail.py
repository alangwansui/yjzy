# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import Warning



class IrMailServer(models.Model):
    _inherit = "ir.mail_server"


    # @api.model
    # def _get_default_bounce_address(self):
    #     res = super(IrMailServer, self)._get_default_bounce_address()
    #     currenct_uid = self.env.context.get('uid') or self.env.user.id
    #     mail_server = self.search([('user_id','=', currenct_uid)])
    #     if mail_server:
    #         return mail_server.smtp_user
    #     return res
    #

    @api.model
    def _get_default_bounce_address(self):

        currenct_uid = self.env.context.get('uid') or self.env.user.id

        print('====_get_default_bounce_address==currenct_uid=', currenct_uid)

        mail_server = self.search([('user_id','=', currenct_uid)])
        if mail_server:
            return mail_server.smtp_user
        else:
            raise Warning('没有匹配的发送邮箱 UID %' % currenct_uid)





