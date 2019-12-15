
from email.utils import parseaddr

def mail_txt_subtraction_partner(txt, partners):
    if not partners:
        return txt
    res = []
    partner_email_list = partners.mapped('email')


    for i in txt.split(','):
        n, e = parseaddr(i)
        print('=i=', i, n, e, partner_email_list, e in partner_email_list)
        print(n,e, partner_email_list)
        if not (e in partner_email_list):
            res.append(i)

    print('===999=', res)

    x = ','.join(res)

    print('===9991=', x)

    return x









