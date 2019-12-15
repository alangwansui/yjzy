# -*- coding: utf-8 -*-

from . import controllers
from . import models
from . import wizard
from . import report


from odoo import api, SUPERUSER_ID

def pre_init_hook(cr):
    pass
    #env = api.Environment(cr, SUPERUSER_ID, {})
    #cr.execute('alter table product_attribute_value_product_product_rel add id serial;')
    #cr.execute('create sequence product_attribute_value_product_product_rel_id_seq;')
    #cr.execute('''alter table product_attribute_value_product_product_rel alter column id set default nextval('product_attribute_value_product_product_rel_id_seq'::regclass);''')
    #print('==pre_init_hook==finish')







