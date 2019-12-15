# -*- coding: utf-8 -*-
import re
import smtplib
import poplib
import imaplib
import email
from imapclient import IMAPClient
from email.mime.text import MIMEText
from email.header import Header
from email.header import decode_header


def parser_header(s):
    """
    #decode_header 返回 （字符，编码）的二元组列表，解码后连接，得到完整字符串
    """
    res = ''
    for content, charset in decode_header(s):
        if charset != None:
            c = content.decode(charset)
        else:
            c = content.decode('ascii')
        res += c
    return res


#登录邮箱账号
imap_server_host = "imap.exmail.qq.com"
email_address = "zhengyijin@tenyale.com"
email_password = "Jzy112233"
mail = imaplib.IMAP4_SSL(imap_server_host)
mail.login(email_address, email_password)



#客户端，列出邮箱目录
mail_server = IMAPClient(imap_server_host, use_uid=True, ssl=False)
res = mail_server.login(email_address, email_password)
print(res)
res = mail_server.list_folders()
for i in res:
    print(i[0][0].decode('utf-7'))


# ##选择目录
# res = mail.select('cehi ')
# print('====select====',res)
# #选择邮件
# result, ids = mail.search(None, "ALL")
# print('====search====',result, ids)
#
#
#
# str_ids = ids[0].decode('utf-8').split()
#
#
# typ, datas= mail.fetch('1', '(RFC822)')
# msg_byte = datas[0][1]


#
# msg_str = msg_byte.decode('gbk')
#
# msg = email.message_from_bytes(msg_byte)
# dh = parser_header(msg['From'])
# print (dh)
# #print ( dh[0][0].decode(dh[0][1]) )









    #
    #
    #
    # mailText = data[0][1].decode(charset)
    # msg = email.message_from_string(mailText)
    # print( msg, charset)

















