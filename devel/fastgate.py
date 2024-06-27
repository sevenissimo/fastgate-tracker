import requests, json, re

class FASTGate:

	def __init__(self, host, user, pswd):
		self.host = host
		resp = requests.get(
			"http://"+self.host+"/status.cgi",
			params={"cmd": "3", "nvget": "login_confirm", "username": user, "password": pswd},
			headers={"X-XSRF-TOKEN": "0"},
			timeout=2)
		self.cookies = resp.cookies
		self.session = resp.json()["login_confirm"]["check_session"]

	def get_devices(self):
		data = {}
		resp = requests.get(
			"http://"+self.host+"/status.cgi",
			params={"nvget": "connected_device_list", "sessionKey": self.session},
			cookies=self.cookies,
			timeout=10)
		data = resp.json()["connected_device_list"]
		print(data)

		# Return unparsed json
		#return data

		# Return a list
		#return [y for (x,y) in data.items() if x.endswith("_mac")]

		# Return mac2name dict (if we trust data is sorted, as it seems to be)
		return dict(zip( [y.upper() for (x,y) in data.items() if x.endswith("_mac")], [y for (x,y) in data.items() if x.endswith("_name")] ))

		# Return structured data2
		data2 = {}
		def _get_id(key): return ''.join([c for c in key if 48 <= ord(c) <= 57])

		for (key, val) in data.items():
			if key.endswith("_mac"):
				data2.setdefault(_get_id(key), {})['mac'] = val.upper()
			if key.endswith("_name"):
				data2.setdefault(_get_id(key), {})['name'] = val
		return data2

		# Return something I don't even remember what is it...
		# for (key, val) in resp.json()["connected_device_list"].items():
		# 	try: (_, id, info) = re.split('_', key, 2)
		# 	except: continue
		# 	data2.setdefault(id, {})[info] = val
		# return data2


f = FASTGate("192.168.1.254", "admin", "secret_pswd")
print(f.get_devices())
