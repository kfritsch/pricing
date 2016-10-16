# comp_http_client.py

import httplib
import sys
from os.path import join, realpath, dirname, isdir

http_server = sys.argv[1]

conn = httplib.HTTPConnection(http_server)

while(1):
	cmd = raw_input('input command (ex. GET test.html: ')
	cmd = cmd.split()

	if(cmd[0] == 'exit'):
		break

	conn.request(cmd[0], cmd[1])

	rsp = conn.getresponse()

	print(rsp.status, rsp.reason)
	data_received = rsp.read()
	print(data_received[0])
	file_dir = "/home/kai/Workspace/test/"
	filename = "test.json"
	f=open(join(file_dir,filename),"w")
	f.write(data_received)
	f.close()

conn.close()