# -*- coding: utf-8 -*-
from imbox import Imbox


with Imbox("imap.exmail.qq.com",
        username='zhengyijin@tenyale.com',
        password='Jzy112233',
        ssl=False,
        ssl_context=None,
        starttls=False) as imbox:
    status, folders_with_additional_info = imbox.folders()

    print(status, folders_with_additional_info)

    messages_in_folder_social = imbox.messages(folder='INBOX')

    for uid, message in messages_in_folder_social:
        print(uid, dir(message))
        print(message.cc, message.bcc, message.sent_to)
