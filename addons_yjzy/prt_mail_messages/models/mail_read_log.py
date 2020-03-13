from odoo import fields, models, api
from requests import get
import json


class mail_read_log(models.Model):
    _name = "mail.read.log"
    _rec_name = 'ip_address'
    _order = 'id desc'
    _description = '邮件客户读取记录'

    mail_id = fields.Many2one('mail.mail', '邮件')
    message_id = fields.Many2one('mail.message', '消息')
    ip_address = fields.Char('IP地址', required=False)
    ip_info_id = fields.Many2one('ip.info', 'IP地址信息', compute='compute_ip_info', store=True)

    country = fields.Char('国家', related='ip_info_id.country')
    region = fields.Char('省', related='ip_info_id.region')
    city = fields.Char('城市', related='ip_info_id.city')
    street = fields.Char('街道', related='ip_info_id.street')
    zip = fields.Char('邮编', related='ip_info_id.zip')

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
    _ipapi_url = 'http://ip-api.com/json/'

    ip = fields.Char('IP地址', required=False)
    content = fields.Text('信息内容')
    no_done = fields.Boolean('未抓取', default=True)
    is_ok = fields.Boolean('成功抓取')
    error = fields.Text('错误信息')
    country = fields.Char('国家')
    region = fields.Char('省')
    city = fields.Char('城市')
    street = fields.Char('街道')
    zip = fields.Char('邮编')

    def get_bidu(self):
        """
        http://api.map.baidu.com/location/ip?ak=您的AK&ip=您的IP&coor=bd09ll //HTTP协议
        """
        ak = self.env['ir.config_parameter'].sudo().get_param('baidu_app_key')
        try:
            for one in self:
                response = get(self._baidu_url, params={'ak': ak, 'ip': one.ip, 'coor': 'bd09ll'})
                res = json.loads(response.content)

                if res['status'] == 0:
                    #print('===', json.loads(response.content))
                    info = res.get('content').get('address_detail')
                    #print('===', info, type(info))
                    one.country = '中国'
                    one.region = info.get('province')
                    one.city = info.get('city')
                    one.street = info.get('street', '') + info.get('street_number', '')
                    one.content = '%s' % res
                    one.no_done = False
                    one.is_ok = True

                elif res['status'] == 1:
                    one.get_ipapi_url()
                else:
                    pass

        except Exception as e:
            one.error = '%s' % e
            print('==get_bidu==', e)

    def get_ipapi_url(self):
        try:
            for one in self:
                response = get(self._ipapi_url + one.ip)
                #print('==get_ipapi_url==start1',  json.loads(response.content))
                res = json.loads(response.content)
                #print('==get_ipapi_url==start2', res, res.get('status'))
                if res.get('status') == 'success':
                    one.content = '%s' % res
                    one.country = '%s:%s' % (res.get('countryCode'), res.get('country'))
                    one.region = '%s:%s' % (res.get('region'), res.get('regionName'))
                    one.city = res.get('city')
                    one.zip = res.get('zip')
                    one.no_done = False
                    one.is_ok = True
                else:
                    one.content = '%s' % res

        except Exception as e:
            one.error = '%s' % e
            #print('==get_ipapi_url==', e)


    @api.model
    def get_bidu_all(self):
        todo = self.search([('no_done', '=', True)])
        todo.get_bidu()



