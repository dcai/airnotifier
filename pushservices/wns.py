from pushservice import PushService
import requests
import logging
import time

class WNSException(Exception): pass

class WNSInvalidPushTypeException(WNSException):
    def __init__(self, regids):
        Exception.__init__(self, "WNS: Invalid push notification type")

WNSACCESSTOKEN_URL = 'https://login.live.com/accesstoken.srf'
TOAST_XML = """
<toast>
    <visual>
        <binding template="%s">
            <text id="1">%s</text>
        </binding>
    </visual>
</toast>
"""

TILE_XML = """
<tile>
    <visual>
        <binding template="%s">
        %s
        </binding>
    </visual>
</tile>
"""

BADGE_XML = """
<badge value="%s" />
"""

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
        if wnstype in ['toast', 'tile', 'badge', 'raw']:
            wnstype = "wns/" + wnstype
        else:
            raise WNSInvalidPushTypeException()

        if wnstype == 'toast':
            template = 'ToastText01'
            xml = TOAST_XML % (template, message)
        elif wnstype == 'tile':
            if 'tile' in wnsparams:
                if 'text' in wnsparams['tile']:
                    template = 'TileSquare150x150Text01'
                    text = wnsparams['tile']['text']
                    xml = ""
                    count = 1
                    for t in text:
                        xml = xml + "<text id='%d'>%s</text>" % (count, t)
                        count = count + 1
                    xml = TILE_XML % (template, xml)
                else:
                    raise WNSInvalidPushTypeException()
            else:
                raise WNSInvalidPushTypeException()
        elif wnstype == 'badge':
            if 'badge' in wnsparams:
                if 'value' in wnsparams['badge']:
                    badgevalue = wnsparams['badge']['value']
                    xml = BADGE_XML % badgevalue
                else:
                    raise WNSInvalidPushTypeException()
            else:
                raise WNSInvalidPushTypeException()
        else:
            raise WNSInvalidPushTypeException()

        accesstoken = self.accesstoken
        if self.expiry <= now:
            accesstoken = self.request_token()
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
