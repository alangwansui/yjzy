from odoo_rpc_client import Client

# assume that odoo server is listening localhost on standard 8069 port and
# have database 'my_db'.
client = Client('localhost', 'yjzy2', 'admin', 'admin')

# get current user
client.user
print(client.user_context, dir(client.user))


# Model browsing
partner_obj = client['res.partner']
records_ids = partner_obj.search([])
for one in partner_obj.browse(records_ids):
    if one.street:
        print(one.name, one.street)
