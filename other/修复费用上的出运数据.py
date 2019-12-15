# -*- coding: utf-8 -*-



from odoo_rpc_client import Client

# assume that odoo server is listening localhost on standard 8069 port and
# have database 'my_db'.
client = Client('localhost', 'my_db', 'user', 'password')

# get current user
client.user
print(client.user.name)

# simple rpc calls
client.execute('res.partner', 'read', [user.partner_id.id])

# Model browsing
SaleOrder = client['sale.order']
s_orders = SaleOrder.search_records([])
for order in s_orders:
    print(order.name)
    for line in order.order_line:
        print("\t%s" % line.name)
    print("-" * 5)
    print()