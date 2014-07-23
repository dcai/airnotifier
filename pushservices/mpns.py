from pushservice import PushService
import requests
import logging

class MPNSClient(PushService):
    def __init__(self, masterdb, app, instanceid=0):
        self.app = app
        self.masterdb = masterdb
    def process(self, **kwargs):
        url = kwargs['token']
        message = kwargs['alert']
        mpnsparams = kwargs['mpns']
        target = 'toast'
        if 'target' in mpnsparams:
            target = mpnsparams['target']

        interval = 1
        if 'interval' in mpnsparams:
            interval = mpnsparams['interval']
        xml = """
            <?xml version="1.0" encoding="utf-8"?>
            <wp:Notification xmlns:wp="WPNotification">
               <wp:Toast>
                    <wp:Text1>%s</wp:Text1>
               </wp:Toast>
            </wp:Notification>
            """ % message
        headers = {
                'Content-Type': 'text/xml',
                'X-WindowsPhone-Target': target,
                'X-NotificationClass': interval,
                }
        response = requests.post(url, data=xml, headers=headers)
        if response.status_code != 200:
            logging.info('MPNS: something bad happened')