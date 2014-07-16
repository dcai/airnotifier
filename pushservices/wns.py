from pushservice import PushService
import requests
import logging
import time

class WNSClient(PushService):
    def __init__(self, clientid, clientsecret, accesstoken, tokentype, expiry):
        self.clientid = clientid
        self.clientsecret = clientsecret
        self.accesstoken = accesstoken
        self.tokentype = tokentype
        self.expiry = expiry

    def send(self, url, message):
        now = int(time.time())
        accesstoken = self.accesstoken
        if self.expiry <= now:
            accesstoken = self.request_token()
        xml1 = '<toast launch=""><visual lang="en-US"><binding template="ToastImageAndText01"><image id="1" src="World" /><text id="1">%s</text></binding></visual></toast>' % message
        xml = """
            <toast>
                <visual>
                    <binding template="ToastText01">
                        <text id="1">bodyText</text>
                    </binding>
                </visual>
            </toast>
            """
        headers = {
                'Content-Type': 'text/xml',
                'X-WNS-Type': 'wns/tile',
                'Authorization': 'Bearer %s' % (accesstoken),
                }
        response = requests.post(url, data=xml, headers=headers)
        if response.status_code == 400:
            logging.info('400 Bad Request: One or more headers were specified incorrectly')
        elif response.status_code == 401:
            pass
        elif response.status_code >= 500:
            pass

        return message

    def request_token(self):
        url = 'https://login.live.com/accesstoken.srf'
        payload = {'grant_type': 'client_credentials', 'client_id': self.clientid, 'client_secret': self.clientsecret, 'scope': 'notify.windows.com'}
        response = requests.post(url, data=payload)
        responsedata = response.json()
        accesstoken = responsedata['access_token']
        return accesstoken
