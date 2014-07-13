import requests
import logging
import time

class WNSClient(object):
    def __init__(self, clientid, clientsecret, accesstoken, tokentype, expiry):
        self.clientid = clientid
        self.clientsecret = clientsecret
        self.accesstoken = accesstoken
        self.tokentype = tokentype
        self.expiry = expiry
    def send(self, url, message):
        now = int(time.time())
        if self.expiry <= now:
            pass
        accesstoken = self.request_token()
        payload = '<toast launch=""><visual lang="en-US"><binding template="ToastImageAndText01"><image id="1" src="World" /><text id="1">%s</text></binding></visual></toast>' % message
        headers = {
                'Content-Type': 'text/xml',
                'X-WNS-RequestForStatus': True,
                'X-WNS-Type': 'wns/toast',
                'Authorization': 'Bearer %s' % (accesstoken),
                }
        logging.info(headers)
        response = requests.post(url, data=payload, headers=headers)
        logging.info(response.status_code)
        if response.status_code == 400:
            pass
        elif response.status_code == 401:
            pass
        elif response.status_code >= 500:
            pass

        logging.info(response.headers)
        return message
    def request_token(self):
        url = 'https://login.live.com/accesstoken.srf'
        payload = {'grant_type': 'client_credentials', 'client_id': self.clientid, 'client_secret': self.clientsecret, 'scope': 'notify.windows.com'}
        response = requests.post(url, data=payload)
        responsedata = response.json()
        accesstoken = responsedata['access_token']
        logging.info(accesstoken)
        return accesstoken
