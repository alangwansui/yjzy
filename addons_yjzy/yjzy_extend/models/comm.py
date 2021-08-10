BACK_TAX_RATIO = 1.13

sfk_type = [
    ('rcskd', u'日常收款单'),#Y
    ('rcfkd', u'日常付款单'),#Y中文改成付款申请单
    ('rcfksqd', u'日常付款申请单'),#费用和其他收入产生的。后续版本可以取消
    ('rcskrld', u'日常收款认领单'),  #针对费用的
    ('rcsktsrld',u'收款退税申报认领单'),
    ('nbzz', u'内部转账'),
    ('jiehui', u'结汇'),
    ('yshxd', u'应收认领单'),
    ('yfhxd', u'应付申请单'),
    ('ysrld', u'预收认领单'),
    ('yfsqd', u'预付申请单'),
    ('yingshourld',u'应收流水'),
    ('yingfurld',u'应付流水'),
    ('tuishuirld',u'退税申报账单'),
    ('fkzl',u'付款指令'),#Y
    ('fksqd',u'付款申请单'),
    ('reconcile_ysrld',u'预收核销'),
    ('reconcile_yfsqd',u'预付核销'),
    ('reconcile_yingshou', u'应收核销'),
    ('reconcile_tuishui', u'退税核销'),
    ('reconcile_yingfu', u'应付核销'),

]

invoice_attribute_all_in_one = [
    ('110',u'主账单应收'),
    ('120', u'主账单应付'),
    ('130', u'主账单退税'),
    ('210', u'增加采购应收'),
    ('220', u'增加采购应付'),
    ('230', u'增加采购退税'),
    ('310', u'费用转货款应收'),
    ('320', u'费用转货款应付'),
    ('330', u'费用转货款退税'),
    ('410', u'其他应收'),
    ('510', u'其他应付'),
    ('620',u'综合退税'),
    ('630',u'退税申报调节'),
    ('640',u'退税申报账单'),
]




