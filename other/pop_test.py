
from email.utils import formataddr, parseaddr
import email, getpass, poplib, sys

hostname = 'imap.exmail.qq.com'
user = 'zhengyijin@tenyale.com'
passwd = 'Jzy112233'

p = poplib.POP3_SSL(hostname) #与SMTP一样，登录gmail需要使用POP3_SSL() 方法，返回class POP3实例
try:
    # 使用POP3.user(), POP3.pass_()方法来登录个人账户
    p.user(user)
    p.pass_(passwd)
except poplib.error_proto: #可能出现的异常
    print('login failed')
else:
    response, listings, octets = p.list()
    for listing in listings:
        number, size = listing.split() #取出message-id
        number = bytes.decode(number)
        size = bytes.decode(size)
        print('Message', number, '( size is ', size, 'bytes)')
        response, lines, octets = p.top(number , 0)
        # 继续把Byte类型转化成普通字符串
        for i in range(0, len(lines)):
            lines[i] = bytes.decode(lines[i])
        #利用email库函数转化成Message类型邮件
        message = email.message_from_string('\n'.join(lines))


        print('===', message.get('cc'), message.get('Received'))

        print('???', parseaddr(message.get('Received')))