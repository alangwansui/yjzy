import html2text
from odoo import _, api, exceptions, fields, models, tools, SUPERUSER_ID
import logging
from odoo.tools import pycompat, ustr
from email.utils import parseaddr
from email._parseaddr import AddrlistClass
from odoo.exceptions import MissingError, AccessError
from .mail_tools import mail_txt_subtraction_partner

_logger = logging.getLogger(__name__)

TREE_VIEW_ID = False
FORM_VIEW_ID = False

# List of forbidden models
FORBIDDEN_MODELS = ['mail.channel']

# Search for 'ghost' models is performed
GHOSTS_CHECKED = False






################
# Mail.Message #
################
class PRTMailMessage(models.Model):
    _inherit = "mail.message"


    def tip_button(self):
        # action_id = self.env.context['params'].get('action')
        # action = self.env['ir.actions.act_window'].browse(action_id)
        # form = action.view_ids.filtered(lambda x: x.view_mode == 'form').view_id

        xml_id = self.env.context.get('form_xml_id')
        form = self.env.ref(xml_id)
        ctx = self.env.context.copy()

        return {
            'name': u'邮件',
            'res_model': self._inherit,
            'res_id': self.id,
            'view_type': 'tree,form',
            "view_mode": 'form',
            "view_id": form.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'auto_search':False,
            'flags': {'initial_mode': 'readonly'},
            'context': ctx,
        }



    @api.depends('personal_partner_ids', 'personal_partner_cc_ids', 'personal_author_id',
                 'author_id', 'partner_ids', 'partner_cc_ids', 'alias_user_id')
    def compute_all_partner(self):
        print('==compute_all_partner==', self)
        for one in self:
            if self._name != 'mail.message':
                continue

            try:

                all_personal = one.personal_partner_ids | one.personal_partner_cc_ids | one.personal_author_id
                all_partners = one.author_id | one.partner_ids | one.partner_cc_ids
                all_users = one.alias_user_id | one.author_id.user_ids

                one.all_partner_ids = all_partners
                one.all_personal_ids = all_personal
                one.inner_partner_ids = all_personal.mapped('partner_id')
                one.all_user_ids = all_users

            except Exception as e:
                pass




    @api.depends('alias_user_id', 'author_id', 'process_type')
    def compute_owner_user(self):
        for one in self:
            if self._name != 'mail.message':
                continue
            if one.process_type == 'in':
                one.owner_user_id = one.alias_user_id
            elif one.process_type == 'out':
                one.owner_user_id = one.author_id.user_ids and one.author_id.user_ids[0] or one.create_uid




    state_delete = fields.Selection([('normal', '正常'),('recycle', '回收站')], '删除状态', default='normal')

    process_type = fields.Selection([('in', u'收件'), ('out', u'发件')], u'类型')

    author_display = fields.Char(string="Author", compute="_author_display")

    # Fields to avoid access check issues
    author_allowed_id = fields.Many2one(string="Author", comodel_name='res.partner',
                                        compute='_get_author_allowed',
                                        search='_search_author_allowed')

    partner_allowed_ids = fields.Many2many(string="Recipients", comodel_name='res.partner',
                                           compute='_get_partners_allowed')

    attachment_allowed_ids = fields.Many2many(string="Attachments", comodel_name='ir.attachment',
                                              compute='_get_attachments_allowed')

    subject_display = fields.Char(string="Subject", compute="_subject_display")
    partner_count = fields.Integer(string="Recipients count", compute='_partner_count')
    record_ref = fields.Reference(string="Message Record", selection='_referenceable_models',
                                  compute='_record_ref')
    attachment_count = fields.Integer(string="Attachments count", compute='_attachment_count')
    thread_messages_count = fields.Integer(string="Messages in thread", compute='_thread_messages_count',
                                           help="Total number of messages in thread")
    ref_partner_ids = fields.Many2many(string="Followers", comodel_name='res.partner',
                                       compute='_message_followers')
    ref_partner_count = fields.Integer(string="Followers", compute='_ref_partner_count')

    mail_mail_ids = fields.One2many(strting="Email Message", comodel_name='mail.mail', inverse_name='mail_message_id',
                                    auto_join=True)
    is_error = fields.Boolean(string="Sending Error", compute='_get_send_error')

    compose_id = fields.Many2one('mail.compose.message', u'底稿')
    fetchmail_server_id = fields.Many2one('fetchmail.server', u'收件服务器')

    email_to = fields.Char(u'发给')
    email_cc = fields.Char('抄送')
    email_bcc = fields.Char('密送')

    manual_to = fields.Char(u'收件人2')
    manual_cc = fields.Char(u'抄送2')
    partner_cc_ids = fields.Many2many('res.partner', 'mail_message_cc_res_partner_rel', 'message_id', 'partner_id', u'抄送人')
    partner_bcc_ids = fields.Many2many('res.partner', 'mail_message_bcc_res_partner_rel', 'message_id', 'partner_id', u'密送人')

    alias_id = fields.Many2one('mail.alias',  u'别名')

    alias_user_id = fields.Many2one('res.users',  related='alias_id.alias_user_id', string=u'别名用户', store=True)

    force_notify_email = fields.Boolean(u'强制使用邮件发送')

    active = fields.Boolean('有效', default=True)
    have_read = fields.Boolean(u'已读')
    had_replied = fields.Boolean(u'已回复', default=False)
    color = fields.Integer('颜色')
    star = fields.Boolean('标星')

    body_text = fields.Text('正文文本呢', compute='compute_body_text', store=False)

    personal_partner_ids = fields.Many2many('personal.partner', 'ref_personal_message', 'cid', 'mid',  u'收件人:通讯录')
    personal_partner_cc_ids = fields.Many2many('personal.partner', 'refcc_personal_message', 'cid', 'mid',  u'抄送:通讯录')
    personal_author_id = fields.Many2one('personal.partner', u'作者:通讯录')

    inner_partner_ids = fields.Many2many('res.partner', 'ref_inner_partner_personal', 'cid', 'pid',  u'内部联系人', compute=compute_all_partner, store=True)

    all_partner_ids = fields.Many2many('res.partner', 'ref_all_partner', 'pid', 'mid',  u'所有伙伴', compute=compute_all_partner, store=True)
    all_personal_ids = fields.Many2many('personal.partner', 'ref_all_personal', 'personal_id', 'partner_id',  u'所有通讯录', compute=compute_all_partner, store=True)
    all_user_ids = fields.Many2many('res.users', 'ref_all_users', 'iud', 'mid',  u'所有用户', compute=compute_all_partner, store=True)


    is_repeated = fields.Boolean('重复标记')

    owner_user_id = fields.Many2one('res.users', '属于用户', compute='compute_owner_user', store=True)


    read_img = fields.Binary('已读图片', compute='compute_read_img')
    replay_img = fields.Binary('已回图片', compute='compute_read_img')

    @api.depends('have_read')
    def compute_read_img(self):
        img_have_read = self.env['ir.attachment'].search([('name', '=', 'message_have_read')], limit=1)
        img_no_read = self.env['ir.attachment'].search([('name', '=', 'message_no_read')], limit=1)
        img_have_replay = self.env['ir.attachment'].search([('name', '=', 'message_have_replay')], limit=1)
        img_no_replay = self.env['ir.attachment'].search([('name', '=', 'message_no_replay')], limit=1)


        img_have_read = tools.image_resize_image(img_have_read.datas, (50, None))
        img_no_read = tools.image_resize_image(img_no_read.datas, (50, None))
        img_have_replay = tools.image_resize_image(img_have_replay.datas, (50, None))
        img_no_replay = tools.image_resize_image(img_no_replay.datas, (50, None))

        for one in self:
            if one.have_read:
                one.read_img = img_have_read
                if one.had_replied:
                    one.read_img = img_have_replay
            else:
                one.read_img = img_no_read




    @api.model
    def cron_histroy_out(self):
        records = self.search([('message_type','=','email'), ('fetchmail_server_id', '=', False), ('process_type', '=', False)])
        records.write({'process_type': 'out'})

    @api.model
    def cron_histroy_is_repeated(self):
        sql_str = "select  message_id  from mail_message where message_type = 'email' and (is_repeated is null or is_repeated = 'f' ) group by message_id having count(message_id)>1;"
        self._cr.execute(sql_str)
        for info in self._cr.dictfetchall():
            recoreds = self.search([('is_repeated','!=',True),('message_id', '=', info['message_id'])]).filtered(lambda x: x._name == 'mail.message')

            if len(recoreds) > 1:
                recoreds[:-1].write({'is_repeated': True })


    @api.depends('body')
    def compute_body_text(self):
        for one in self:
            body_text = html2text.html2text(one.body)
            one.body_text = body_text

    def edit_again(self):
        compose = self.compose_id
        #收件的回复是会把发件人加到收件人名单里，而发件的回复，不需要把发件人加入
        default_partner_ids = compose.partner_ids and [x.id for x in compose.partner_ids] or None
        default_partner_cc_ids = compose.partner_cc_ids and [x.id for x in compose.partner_cc_ids] or None
        ctx = {
            'default_model': compose.model,
            'default_res_id': compose.res_id,
            'default_partner_ids': default_partner_ids,
            'default_partner_cc_ids': default_partner_cc_ids,
            'default_manual_cc': compose.manual_cc,
            'default_manual_to': compose.manual_to,
            'default_email_from': compose.email_from,
            'default_email_to': compose.email_to,
            'default_subject': compose.subject,
            'default_body': compose.body,
            'default_force_notify_email': compose.force_notify_email,
            'default_attachment_ids': compose.attachment_ids and [(6, 0, [x.id for x in compose.attachment_ids])] or False,
            'default_personal_partner_ids': compose.personal_partner_ids and [(6, 0, [x.id for x in compose.personal_partner_ids])] or False,
            'default_personal_partner_cc_ids': compose.personal_partner_cc_ids and [(6, 0, [x.id for x in compose.personal_partner_cc_ids])] or False,
        }

        print('=====ctx', compose.id, compose.personal_partner_cc_ids)

        # 再次编辑：         直接复制底稿，什么都不改动
        # 回复全部   ：  复制底稿，底稿body前面 + 签名
        again_type = self.env.context.get('again_type', '')
        if again_type == 'out_again':
            pass
        if again_type == 'out_all':
            body = (_(
                "  <div font-style=normal;><br/><br/><br/>%s<br/><br/><br/></div><div style=font-size:13px; ><div style=background-color:#efefef>----- Original Mail----- <br/> Date: %s <br/> From: %s <br/> Subject: %s </div><br/><br/>%s</div>") %
                    (self.env.user.signature or '', str(self.date), self.author_display, self.subject_display, self.body))
            ctx.update({'default_body' :body})

        return {
            'name': _("New message"),
            "views": [[False, "form"]],
            'res_model': 'mail.compose.message',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': ctx,
        }


    def toggle_have_read(self):
        self.ensure_one()
        self.have_read = not self.have_read


    @api.model
    def cron_create_personal(self, domain=None):
        domain = domain or []
        domain += [('message_type', '=', 'email')]
        for one in self.search(domain):
            one.make_one_personal()

    def parse_address_make_personal(self, addrss, user):
        print('==parse_address_make_personal==', addrss, user)
        personal_obj = self.env['personal.partner']
        default_tag = self.env.ref('prt_mail_messages.personal_tag_income_tmp')
        records = self.env['personal.partner']

        before_name = ''
        for name, addr in AddrlistClass(addrss).getaddrlist():
            if not ('@' in  addr): continue
            print('==parse_address_make_personal==', name, addr, user.id)
            addr = addr.lower()
            personal = personal_obj.search([('email', '=', addr),('user_id', '=', user.id)])
            if not personal:
                personal = personal_obj.create({
                    'name': name,
                    'email': addr,
                    'user_id': user.id,
                    'tag_id': default_tag.id,
                })
            records |= personal
        return records

    def make_one_personal(self):
        print('========make_one_personal==========', self.process_type)
        if self.process_type == 'in':
            self.make_one_personal_in()
        if self.process_type == 'out':
            self.make_one_personal_out()


    def make_one_personal_out(self):
        print('========make_one_personal out==========', self, self.process_type, self.author_id, self.author_id.user_ids)
        users = self.author_id.user_ids
        if not users:
            return False
            #raise Warning('没找到对应的作者 %s' % self.id)

        user = users[0]

        if self.manual_to:
            self.personal_partner_ids |= self.parse_address_make_personal(self.email_to, user)
        if self.email_cc:
            self.personal_partner_cc_ids |= self.parse_address_make_personal(self.email_cc, user)
        if self.email_from:
            personal_author = self.parse_address_make_personal(self.email_from, user)
            for i in personal_author:
                print('>>', i.name, i.email)

            self.personal_author_id = self.parse_address_make_personal(self.email_from, user)


    def make_one_personal_in(self, user=False):
        user = user or self.alias_user_id
        if not user:
            return False
            #raise Warning('没找到对应的别名用户id:%s' % self.id)
        if self.email_to:
            self.personal_partner_ids |= self.parse_address_make_personal(self.email_to, user)
        if self.email_cc:
            self.personal_partner_cc_ids |= self.parse_address_make_personal(self.email_cc, user)
        if self.email_from:
            self.personal_author_id = self.parse_address_make_personal(self.email_from, user)



    def make_privace_comment(self):
        channel = self.env['mail.channel'].sudo().search([('channel_type','=','chat'), ('chat_uid','!=',False), ('chat_uid','=', self.alias_id.alias_user_id.id)], limit=1)
        print('==make_privace_comment===', self.alias_id.alias_user_id, self.env.user, self.env.context, channel)
        if self.alias_id.alias_user_id and channel:
            channel.message_post(
                body=u'新邮件 %s 来自:%s' % (self.subject, self.email_from),
                content_subtype="html",
                message_type="comment",
                subtype="mail.mt_comment",
            )

    @api.model
    def create(self, values):

        #print('-------------123----------------------------------------', values['email_to'], self.env.context)
        msg = super(PRTMailMessage, self).create(values)

        #<jon> 收件服务器创建消息
        if msg.fetchmail_server_id:
            msg.manual_to = mail_txt_subtraction_partner(msg.email_to, msg.partner_ids)
            msg.manual_cc = mail_txt_subtraction_partner(msg.email_cc, msg.partner_cc_ids)

        #<jon> 发邮件
        else:
            msg.process_type = 'out'

        #判定重复标记
        if self._name == 'mail.message':
            repeated_msg = self.with_context(active_test=False).search([('message_id', '=', msg.message_id)]).filtered(lambda x: x._name == 'mail.message')
            print('==repeated_msg===', self,  repeated_msg, repeated_msg._name )

            if len(repeated_msg) > 1:
                msg.is_repeated = True

        return msg


    # -- Unlink
    @api.multi
    def unlink(self):

        # Superuser?
        if self.env.user.id == SUPERUSER_ID:
            return super(PRTMailMessage, self).unlink()

        # Force delete ?
        if self._context.get('force_delete', False):
            return super(PRTMailMessage, self).unlink()

        # Can delete messages?
        if not self.env.user.has_group('prt_mail_messages.group_delete'):
            raise AccessError(_("You cannot delete messages!"))

        # Can delete any message
        if self.env.user.has_group('prt_mail_messages.group_delete_any'):
            return super(PRTMailMessage, self).unlink()

        partner_id = self.env.user.partner_id.id
        for rec in self:
            """
            Can delete if user:
            - Is Message Author for 'comment' message
            - Is the only 'recipient' for 'email' message            
            """
            # Sent
            if rec.message_type == 'comment':
                # Is Author?
                if not rec.author_allowed_id.id == partner_id:
                    raise AccessError(_("You cannot delete the following message"
                                        "\n\n Subject: %s \n\n"
                                        " Reason: %s" % (rec.subject_display, _("You are not the message author"))))

            # Received
            if rec.message_type == 'email':
                # No recipients
                if not rec.partner_ids:
                    raise AccessError(_("You cannot delete the following message"
                                        "\n\n Subject: %s \n\n"
                                        " Reason: %s" % (rec.subject_display,
                                                         _("Message recipients undefined"))))

                # Has several recipients?
                if len(rec.partner_ids) > 1:
                    raise AccessError(_("You cannot delete the following message"
                                        "\n\n Subject: %s \n\n"
                                        " Reason: %s" % (rec.subject_display,
                                                         _("Message has multiple recipients"))))

                # Partner is not that one recipient
                if not rec.partner_ids[0].id == partner_id:
                    raise AccessError(_("You cannot delete the following message"
                                        "\n\n Subject: %s \n\n"
                                        " Reason: %s" % (rec.subject_display,
                                                         _("You are not the message recipient"))))

        return super(PRTMailMessage, self).unlink()

    # -- Check if error while sending TODO check log
    @api.depends('notification_ids')
    @api.multi
    def _get_send_error(self):
        for rec in self.filtered(lambda m: m.notification_ids.mapped('email_status') not in ['sent']):
            if len(rec.mail_mail_ids.filtered(lambda m: m.state == 'exception')) > 0:
                rec.is_error = True

    # -- Count ref Partners
    @api.multi
    def _ref_partner_count(self):
        for rec in self:
            rec.ref_partner_count = len(rec.ref_partner_ids)

    """
    Sometimes user has access to record but does not have access to author or recipients.
    Below is a workaround for author, recipient and followers
    """

    # -- Get allowed author
    @api.depends('author_id')
    @api.multi
    def _get_author_allowed(self):
        forbidden_partners = self.env['res.partner']
        for rec in self:
            author_id = rec.author_id
            if author_id not in forbidden_partners:
                try:
                    author_id.check_access_rule('read')
                    rec.author_allowed_id = author_id
                except:
                    forbidden_partners += author_id

    # -- Get allowed recipients
    @api.depends('attachment_ids')
    @api.multi
    def _get_attachments_allowed(self):
        forbidden_records = []
        for rec in self:
            attachments_allowed = self.env['ir.attachment']
            for attachment in rec.attachment_ids:
                att_obj = attachment.sudo().read(['res_model', 'res_id'])[0]
                model = att_obj.get('res_model', False)
                res_id = att_obj.get('res_id', False)
                if (model, res_id) in forbidden_records:
                    continue
                try:
                    self.env[model].browse(res_id).check_access_rule('read')
                except:
                    forbidden_records += (model, res_id)
                    continue
                attachments_allowed += attachment

            rec.attachment_allowed_ids = attachments_allowed

    # -- Get allowed recipients
    @api.depends('partner_ids')
    @api.multi
    def _get_partners_allowed(self):
        forbidden_partners = self.env['res.partner']
        for rec in self:
            recipients_allowed = self.env['res.partner']
            for partner in rec.partner_ids - forbidden_partners:
                try:
                    partner.check_access_rule('read')
                    recipients_allowed += partner
                except:
                    forbidden_partners += partner

            rec.partner_allowed_ids = recipients_allowed

    # -- Search allowed authors
    @api.model
    def _search_author_allowed(self, operator, value):
        return [('author_id', operator, value)]

    # -- Get related record followers
    """
    Check if model has 'followers' field and user has access to followers
    """

    @api.depends('record_ref')
    @api.multi
    def _message_followers(self):
        forbidden_partners = self.env['res.partner']
        approved_models = []
        for rec in self:
            if rec.record_ref:

                # Check model

                model = rec.model
                if model not in approved_models:
                    if 'message_partner_ids' in self.env[model]._fields:
                        approved_models.append(model)
                    else:
                        continue

                followers_allowed = self.env['res.partner']
                for follower in rec.record_ref.message_partner_ids - forbidden_partners:
                    try:
                        follower.check_access_rule('read')
                        followers_allowed += follower
                    except:
                        forbidden_partners += follower
                rec.ref_partner_ids = followers_allowed

    # -- Dummy
    @api.multi
    def dummy(self):
        return

    # -- Get Subject for tree view
    @api.depends('subject')
    @api.multi
    def _subject_display(self):

        # Get model names first. Use this method to get translated values
        ir_models = self.env['ir.model'].search([('model', 'in', list(set(self.mapped('model'))))])
        model_dict = {}
        for model in ir_models:
            # Check if model has "name" field
            has_name = self.env['ir.model.fields'].sudo().search_count([('model_id', '=', model.id),
                                                                        ('name', '=', 'name')])
            model_dict.update({model.model: [model.name, has_name]})

        # Compose subject
        for rec in self:
            if rec.subject:
                subject_display = rec.subject
            else:
                subject_display = '=== No Reference ==='

            # Has reference


                # Has 'name' field

                # Has subject
                if rec.subject:
                    subject_display = "%s => %s" % (subject_display, rec.subject)

            # Set subject
            rec.subject_display = subject_display

    # -- Get Author for tree view
    @api.depends('author_allowed_id')
    @api.multi
    def _author_display(self):
        for rec in self:
            rec.author_display = rec.author_allowed_id.name if rec.author_allowed_id else rec.email_from

    # -- Count recipients
    @api.depends('partner_allowed_ids')
    @api.multi
    def _partner_count(self):
        for rec in self:
            rec.partner_count = len(rec.partner_allowed_ids)

    # -- Count attachments
    @api.depends('attachment_allowed_ids')
    @api.multi
    def _attachment_count(self):
        for rec in self:
            rec.attachment_count = len(rec.attachment_allowed_ids)

    # -- Count messages in same thread
    @api.depends('res_id')
    @api.multi
    def _thread_messages_count(self):
        for rec in self:
            rec.thread_messages_count = self.search_count(['&', '&',
                                                           ('model', '=', rec.model),
                                                           ('res_id', '=', rec.res_id),
                                                           ('message_type', '!=', 'notification')])

    # -- Ref models
    @api.model
    def _referenceable_models(self):
        # return [(x.model, x.name) for x in self.env['ir.model'].sudo().search([('model', '!=', 'mail.channel')])]
        """
        Mail channel is needed for legacy views (Settings->Technical Settings->Messages)
        """
        return [(x.model, x.name) for x in self.env['ir.model'].sudo().search([('transient', '=', False)])]

    # -- Compose reference
    @api.depends('res_id')
    @api.multi
    def _record_ref(self):
        for rec in self:
            if rec.model:
                if rec.res_id:
                    res = self.env[rec.model].sudo().search([("id", "=", rec.res_id)])
                    if res:
                        rec.record_ref = res

    # -- Get forbidden models
    def _get_forbidden_models(self):

        # Use global vars
        global GHOSTS_CHECKED
        global FORBIDDEN_MODELS

        # Ghosts checked?
        if GHOSTS_CHECKED:
            return FORBIDDEN_MODELS

        # Search for 'ghost' models. These are models left from uninstalled modules.
        self._cr.execute(""" SELECT model FROM ir_model
                                    WHERE transient = False
                                    AND NOT model = ANY(%s) """, (list(FORBIDDEN_MODELS),))

        # Check each model
        for msg_model in self._cr.fetchall():
            model = msg_model[0]
            if not self.env['ir.model'].sudo().search([('model', '=', model)]).modules:
                FORBIDDEN_MODELS.append(model)

        # Mark as checked
        GHOSTS_CHECKED = True
        return FORBIDDEN_MODELS

    # -- Open messages of the same thread
    @api.multi
    def thread_messages(self):
        self.ensure_one()

        global TREE_VIEW_ID
        global FORM_VIEW_ID

        # Cache Tree View and Form View ids
        if not TREE_VIEW_ID:
            TREE_VIEW_ID = self.env.ref('prt_mail_messages.prt_mail_message_tree').id
            FORM_VIEW_ID = self.env.ref('prt_mail_messages.prt_mail_message_form').id

        return {
            'name': _("Messages"),
            "views": [[TREE_VIEW_ID, "tree"], [FORM_VIEW_ID, "form"]],
            'res_model': 'mail.message',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('message_type', '!=', 'notification'), ('model', '=', self.model), ('res_id', '=', self.res_id)]
        }

    # -- Override _search
    """
    mail.message overrides generic '_search' defined in 'model' to implement own logic for message access rights.
    However sometimes it does not work as expected.
    So we use generic method in 'model' and check access rights later in 'search' method.
    Following keys in context are used:
        - 'check_messages_access': if not set legacy 'search' is performed
    """

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if not self._context.get('check_messages_access', False):
            return super(PRTMailMessage, self)._search(args=args, offset=offset, limit=limit, order=order, count=count,
                                                       access_rights_uid=access_rights_uid)

        if expression.is_false(self, args):
            # optimization: no need to query, as no record satisfies the domain
            return 0 if count else []

        query = self._where_calc(args)
        order_by = self._generate_order_by(order, query)
        from_clause, where_clause, where_clause_params = query.get_sql()

        where_str = where_clause and (" WHERE %s" % where_clause) or ''

        if count:
            # Ignore order, limit and offset when just counting, they don't make sense and could
            # hurt performance
            query_str = 'SELECT count(1) FROM ' + from_clause + where_str
            self._cr.execute(query_str, where_clause_params)
            res = self._cr.fetchone()
            return res[0]

        limit_str = limit and ' limit %d' % limit or ''
        offset_str = offset and ' offset %d' % offset or ''
        query_str = 'SELECT "%s".id FROM ' % self._table + from_clause + where_str + order_by + limit_str + offset_str
        self._cr.execute(query_str, where_clause_params)
        res = self._cr.fetchall()

        # TDE note: with auto_join, we could have several lines about the same result
        # i.e. a lead with several unread messages; we uniquify the result using
        # a fast way to do it while preserving order (http://www.peterbe.com/plog/uniqifiers-benchmark)
        def _uniquify_list(seq):
            seen = set()
            return [x for x in seq if x not in seen and not seen.add(x)]

        return _uniquify_list([x[0] for x in res])

    # -- Override read
    """
    Avoid access rights check implemented in original mail.message
    Will check them later in "search"
    Using base model function instead
        Following keys in context are used:
        - 'check_messages_access': if not set legacy 'search' is performed
    """

    def button_read(self):
        self.ensure_one()
        self.have_read = True
        return {
            'name': _("Messages"),
            #"views": [[TREE_VIEW_ID, "tree"], [FORM_VIEW_ID, "form"]],
            'view_mode': 'form',
            'view_id': self.env.ref('prt_mail_messages.prt_mail_message_income_form').id,
            'res_model': 'mail.message',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }


    @api.multi
    def read(self, fields=None, load='_classic_read'):
        print('===read====', self.env.context)

        #<jon> 打开数据，自动标记为已读
        action_ids = [
            #self.env.ref('prt_mail_messages.action_prt_mail_messages').id,
            self.env.ref('prt_mail_messages.action_mail_messages_income').id,
            self.env.ref('prt_mail_messages.action_mail_messages_out').id,
        ]
        #对应的3个动作中读取单据的记录，视为打开记录

        print('>>>>>>>>>', (len(self) ==1 and self.env.context.get('params',{}).get('action', 0) in action_ids) and not self.env.context.get('no_mark_have_read'))

        if (len(self) ==1 and self.env.context.get('params',{}).get('action', 0) in action_ids) and not self.env.context.get('no_mark_have_read'):
            #sql更新数据，读取方法中，不能待用orm的写入方法，死循环
            self._cr.execute('UPDATE %s SET have_read=%s WHERE id=%s' % (self._table, True,  self.id))
        # <jon> 打开数据，自动标记为已读



        if not self._context.get('check_messages_access', False):
            return super(PRTMailMessage, self).read(fields=fields, load=load)



        """
        From here starts the original 'read' code
        """
        # split fields into stored and computed fields
        stored, inherited, computed = [], [], []
        for name in fields:
            field = self._fields.get(name)
            if field:
                if field.store:
                    stored.append(name)
                elif field.base_field.store:
                    inherited.append(name)
                else:
                    computed.append(name)
            else:
                _logger.warning("%s.read() with unknown field '%s'", self._name, name)

        # fetch stored fields from the database to the cache; this should feed
        # the prefetching of secondary records
        self._read_from_database(stored, inherited)

        # retrieve results from records; this takes values from the cache and
        # computes remaining fields
        result = []
        name_fields = [(name, self._fields[name]) for name in (stored + inherited + computed)]
        use_name_get = (load == '_classic_read')

        for record in self:
            try:
                values = {'id': record.id}
                for name, field in name_fields:
                    values[name] = field.convert_to_read(record[name], record, use_name_get)
                result.append(values)
            except MissingError:
                pass

        return result

    # -- Override Search
    """
    Mail message access rights/rules checked must be done based on the access rights/rules of the message record.
    As a workaround we are using 'search' method to filter messages from unavailable records.
    
    Display only messages where user has read access to related record.
    
    Following keys in context are used:
    - 'check_messages_access': if not set legacy 'search' is performed
    - 'force_record_reset': in case message refers to non-existing (e.g. removed) record model and res_id will be set NULL
    """

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):

        if not self._context.get('check_messages_access', False):
            return super(PRTMailMessage, self).search(args=args, offset=offset, limit=limit, order=order, count=count)

        # Store context keys
        force_record_reset = self._context.get('force_record_reset', False)
        # Store initial args in case we need them later
        modded_args = args

        # Define sort order
        if order and ('ASC' in order or 'asc' in order):
            sort_asc = True
        else:
            sort_asc = False

        # Check model access 1st
        forbidden_models = self._get_forbidden_models()

        # Get list of possible followed models
        self._cr.execute(""" SELECT model FROM ir_model
                                        WHERE is_mail_thread = True
                                        AND NOT model = ANY(%s) """, (list(forbidden_models),))

        # Check each model
        for msg_model in self._cr.fetchall():
            if not self.env['ir.model.access'].check(msg_model[0], 'read', raise_exception=False):
                forbidden_models.append(msg_model[0])

        # Add forbidden models condition to domain
        if len(forbidden_models) > 0:
            modded_args.append(['model', 'not in', forbidden_models])

        # Return Count
        if count:
            return super(PRTMailMessage, self).search(args=modded_args, offset=offset, limit=limit, order=order, count=True)

        # Get records
        res_ids = self._search(args=modded_args, offset=offset, limit=limit, order=order, count=False)
        res = self.browse(res_ids)

        # Cache allowed records and store last id
        rec_allowed = []
        last_id = False

        # Now check record rules for each message
        res_allowed = self.env['mail.message']
        len_initial = limit if limit else len(res)
        len_filtered = 0

        # Check records
        """
        Check in we need include "lost" messages. These are messages with no model or res_id
        """
        get_lost = self._context.get('get_lost', False)

        for rec in res:
            model = rec.model
            res_id = rec.res_id

            # Update last id
            rec_id = rec.id
            if sort_asc:
                if not last_id or rec_id > last_id:
                    last_id = rec_id
            else:
                if not last_id or rec_id < last_id:
                    last_id = rec_id

            # No model
            if not model:
                if get_lost:
                    res_allowed += rec
                    len_filtered += 1
                continue

            # No id
            if not res_id:
                if get_lost:
                    res_allowed += rec
                    len_filtered += 1
                continue

            # Check if record is allowed already
            if (model, res_id) not in rec_allowed:
                # Check access rules on record. Skip if refers to deleted record
                try:
                    target_rec = self.env[model].search([('id', '=', res_id)])
                    if not target_rec:
                        # Reset model and res_id
                        if force_record_reset:
                            rec.sudo().write({'model': False, 'res_id': False})
                        continue
                    # Check message record
                    target_rec.check_access_rule('read')
                    rec_allowed.append((model, res_id))
                except:
                    continue

            res_allowed += rec
            len_filtered += 1

        del res  # Hope Python will free memory asap!))

        # Return if initially got less then limit
        if limit is None or len_initial < limit:
            return res_allowed

        len_remaining = len_initial - len_filtered

        # Return if all allowed
        if len_remaining == 0:
            return res_allowed

        # Check last id
        if not last_id:
            return res_allowed

        """
        Step 2+n in case need to get more records
        """
        # Get remaining recs
        while len_remaining > 0:

            new_args = modded_args.copy()
            if sort_asc:
                new_args.append(['id', '>', last_id])
            else:
                new_args.append(['id', '<', last_id])

            # Let's try!))
            res_2_ids = self._search(args=new_args, offset=0, limit=limit, order=order, count=False)
            res_2 = self.browse(res_2_ids)

            if len(res_2) < 1:
                break

            # Check records
            for rec in res_2:
                model = rec.model
                res_id = rec.res_id

                # Update last id
                rec_id = rec.id
                if sort_asc:
                    if not last_id or rec_id > last_id:
                        last_id = rec_id
                else:
                    if not last_id or rec_id < last_id:
                        last_id = rec_id

                # No model
                if not model:
                    if get_lost:
                        res_allowed += rec
                        len_filtered += 1
                    continue

                # No res_id
                if not res_id:
                    if get_lost:
                        res_allowed += rec
                        len_filtered += 1
                    continue

                # Check access rules on record. Skip if refers to deleted record
                if (model, res_id) not in rec_allowed:
                    try:
                        target_rec = self.env[model].search([('id', '=', res_id)])
                        if not target_rec:
                            # Reset model and res_id
                            if force_record_reset:
                                rec.sudo().write({'model': False, 'res_id': False})
                            continue
                        # Check message record
                        target_rec.check_access_rule('read')
                        rec_allowed.append((model, res_id))
                    except:
                        continue

                res_allowed += rec
                len_remaining -= 1

        return res_allowed

    # -- Prepare context for reply or quote message
    @api.multi
    def reply_prep_context(self):
        self.ensure_one()

        ctx = self.env.context
        personal_obj = self.env['personal.partner']
        partner_obj = self.env['res.partner']
        wizard_mode = self._context.get('wizard_mode', '')

        # body = False
        # if wizard_mode in ['quote', 'forward']:
        body = (_(
            "  <div font-style=normal;><br/><br/><br/>%s<br/><br/><br/></div><div style=font-size:13px; ><div style=background-color:#efefef;>----- Original Mail----- <br/> Date: %s <br/> From: %s <br/> Subject: %s </div><br/><br/>%s</div>") %
                (self.env.user.signature or '', str(self.date), self.author_display, self.subject_display, self.body))


        email_from = ''
        email_to = self.email_from
        email_cc = ''
        default_partners = self.author_allowed_id
        cc_partners = False
        manual_to = ''
        manual_cc = ''

        personal_partner = self.personal_author_id
        personal_partner_cc = False
        personal_me = personal_obj.search([('email','=', self.env.user.partner_id.email)])


        #回复全部
        if wizard_mode == 'quote':
            def get_email_to_exclude_fetch_server(msg, fetch_server_mail):
                res = msg.email_from
                for s in msg.email_to.split(','):
                    n, e = parseaddr(s)
                    if e != fetch_server_mail:
                        res += ',' + s
                return res

            email_to = get_email_to_exclude_fetch_server(self, self.fetchmail_server_id.user)
            email_cc = self.email_cc
            default_partners |= self.partner_ids - self.fetchmail_server_id.partner_id
            cc_partners = self.partner_cc_ids

            personal_partner |= self.personal_partner_ids - personal_me
            personal_partner_cc = self.personal_partner_cc_ids - personal_me

            #回复全部，manual_to = email_to - default_partners
            for ss in email_to.split(','):
                nn, ee = parseaddr(ss)
                if ee not in [x.email for x in default_partners]:
                    if not manual_to:
                        manual_to = ss
                    else:
                        manual_to += ',' + ss

            list_manual_cc = []

            if email_cc:
                for i in email_cc.split(','):
                    n, e = parseaddr(i)
                    if e not in cc_partners.mapped('email'):
                        list_manual_cc.append(i)
            if list_manual_cc:
                manual_cc = ','.join(list_manual_cc)

            #如果是
                
        #转发
        elif wizard_mode == 'forward':
            email_from = ''
            email_to = ''
            email_cc = ''
            default_partners -= default_partners
            personal_partner = False
            personal_partner_cc = False
        else:
            pass


        if wizard_mode in ['quote', '', 'replay', False]:
            if not default_partners:
                manual_to = self.email_from


        #非转发必须存在至少一个partner，转发可以自己填写。
        if (wizard_mode != 'forward') and (not default_partners):
            p = partner_obj.search([('email','=', self.email_from)], limit=1)
            if not p:
                Warning(u'需要至少一个合作伙伴，请先创建')

                # name, em = parseaddr(self.email_from)
                # if not name:
                #     name = em
                # p = partner_obj.create({'name':name, 'email': em })
                # default_partners |= p




        #print('====', default_partners, default_partners.mapped('email'))


        #<jon> 别名默认使用发件专用
        default_channel = self.env['mail.channel'].search([('sent_uid', '=', self.env.user.id)], limit=1)
        ctx = {
            'default_res_id': default_channel and default_channel.id or self.res_id,
            'defualt_model': default_channel and default_channel._name or self.model,

            'default_parent_id': False if wizard_mode == 'forward' else self.id,
            'default_partner_ids': default_partners and [x.id for x in default_partners] or False,
            'default_partner_cc_ids': cc_partners and [i.id for i in cc_partners] or False,

            'default_attachment_ids': self.attachment_ids.ids if wizard_mode == 'forward' else [],
            'default_is_log': False,
            'default_body': body,
            'default_wizard_mode': wizard_mode,

            'default_email_to': email_to,
            'default_email_cc': email_cc,
            'default_manual_cc': manual_cc,
            'default_manual_to': manual_to,
            'is_reply': True,
            'mail_notify_user_signature': False,

            'default_personal_partner_ids': personal_partner and [x.id for x in personal_partner] or False,
            'default_personal_partner_cc_ids': personal_partner_cc and [x.id for x in personal_partner_cc] or False,
        }

        if (not wizard_mode) or (wizard_mode == 'quote'):
            ctx.update({
                'default_replay_meesage_id': self.id,
            })

        return ctx

    # -- Reply or quote message
    @api.multi
    def reply(self):
        self.ensure_one()
        return {
            'name': _("New message"),
            "views": [[False, "form"]],
            'res_model': 'mail.compose.message',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': self.reply_prep_context()
        }

    # -- Move message
    @api.multi
    def move(self):
        self.ensure_one()

        return {
            'name': _("Move messages"),
            "views": [[False, "form"]],
            'res_model': 'prt.message.move.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }


#####################
# Mail Move Message #
#####################
class PRTMailMove(models.TransientModel):
    _name = 'prt.message.move.wiz'
    _description = 'Move Messages To Other Thread'

    model_to = fields.Reference(string="Move to", selection='_referenceable_models')
    lead_delete = fields.Boolean(string="Delete Empty Leads",
                                 help="If all messages are moved from lead and there are no other messages"
                                      " left except for notifications lead will be deleted")
    opp_delete = fields.Boolean(string="Delete Empty Opportunities",
                                help="If all messages are moved from opportunity and there are no other messages"
                                     " left except for notifications opportunity will be deleted")

    notify = fields.Selection([
        ('0', 'Do not notify'),
        ('1', 'Log internal note'),
        ('2', 'Send message'),
    ], string="Notify", required=True,
        default='0',
        help="Notify followers of destination record")

    # -- Ref models
    @api.model
    def _referenceable_models(self):
        return [(x.object, x.name) for x in self.env['res.request.link'].sudo().search([])]


# Legacy! keep those imports here to avoid dependency cycle errors
from odoo.osv import expression
