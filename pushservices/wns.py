from pushservice import PushService
import requests
import logging
import time

WNSACCESSTOKEN_URL = 'https://login.live.com/accesstoken.srf'

class WNSClient(PushService):
    def __init__(self, masterdb, app, instanceid=0):
        self.app = app
        self.masterdb = masterdb
        self.clientid = app['wnsclientid']
        self.clientsecret = app['wnsclientsecret']
        self.accesstoken = app['wnsaccesstoken']
        self.tokentype = app['wnstokentype']
        self.expiry = app['wnstokenexpiry']

    def process(self, **kwargs):
        url = kwargs['token']
        message = kwargs['alert']
        now = int(time.time())
        wnsparams = kwargs['wns']
        wnstype = 'toast'
        if 'type' in wnsparams:
            wnstype = wnsparams['type']
        if wnstype in ['toast', 'tile']:
            wnstype = "wns/" + wnstype
        accesstoken = self.accesstoken
        if self.expiry <= now:
            accesstoken = self.request_token()
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
                'X-WNS-Type': wnstype,
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
        payload = {'grant_type': 'client_credentials', 'client_id': self.clientid, 'client_secret': self.clientsecret, 'scope': 'notify.windows.com'}
        response = requests.post(WNSACCESSTOKEN_URL, data=payload)
        responsedata = response.json()
        accesstoken = responsedata['access_token']
        self.app['wnsaccesstoken'] = accesstoken
        self.masterdb.applications.update({'shortname': self.app['shortname']}, self.app, safe=True)
        return accesstoken
