from odoo import fields, models, api
from requests import get
import json


class mail_read_log(models.Model):
    _name = "mail.read.log"
    _rec_name = 'ip_address'
    _description = '邮件客户读取记录'

    mail_id = fields.Many2one('mail.mail', '邮件')
    ip_address = fields.Char('IP地址', required=False)
    ip_info_id = fields.Many2one('ip.info', 'IP地址信息', compute='compute_ip_info', store=True)

    @api.depends('ip_address')
    def compute_ip_info(self):
        info_obj = self.env['ip.info']
        for one in self:
            info = info_obj.search([('ip', '=', one.ip_address)], limit=1)
            if not info:
                info = info_obj.create({'ip': one.ip_address})
            one.ip_info_id = info


class ip_info(models.Model):
    _name = "ip.info"
    _rec_name = 'content'
    _description = 'IP地址信息'
    _baidu_url = 'http://api.map.baidu.com/location/ip'
    _ipapi_url = 'http://ip-api.com/line/'


    ip = fields.Char('IP地址', required=False)
    content = fields.Text('信息内容')
    no_done = fields.Boolean('未抓取', default=True)
    is_ok = fields.Boolean('成功抓取')
    error = fields.Text('错误信息')

    def get_bidu(self):
        """
        http://api.map.baidu.com/location/ip?ak=您的AK&ip=您的IP&coor=bd09ll //HTTP协议
        """
        ak = self.env['ir.config_parameter'].sudo().get_param('baidu_app_key')
        try:
            for one in self:
                response = get(self._baidu_url, params={'ak': ak, 'ip': one.ip, 'coor': 'bd09ll'})
                one.content = '%s' % json.loads(response.content)
                one.no_done = False
        except Exception as e:
            print('==get_bidu==', e)

    def get_ipapi_url(self):
        """
        success
        Canada
        CA
        QC
        Quebec
        Montreal
        H1S
        45.5808
        -73.5825
        America/Toronto
        Le Groupe Videotron Ltee
        Videotron Ltee
        AS5769 Videotron Telecom Ltee
        24.48.0.1
        """

        try:
            for one in self:
                response = get(self._ipapi_url + one.ip)
                print('==get_ipapi_url==', response, response.content)
                one.content = response.content
                one.no_done = False
        except Exception as e:
            print('==get_ipapi_url==', e)


    @api.model
    def get_bidu_all(self):
        todo = self.search([('no_done', '=', True)])
        todo.get_bidu()



