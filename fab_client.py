# deploy.py
import sys
from FAB import FAB_Client


host, func_name =  sys.argv[1], sys.argv[2]


yjzy = FAB_Client(host)
getattr(yjzy, func_name)()

print('__end ok__')


