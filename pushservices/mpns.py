from pushservice import PushService
import requests
import logging

TOAST_XML = """
<?xml version="1.0" encoding="utf-8"?>
<wp:Notification xmlns:wp="WPNotification">
    <wp:Toast>
        <wp:Text1>%s</wp:Text1>
        <wp:Text2>%s</wp:Text2>
        %s
    </wp:Toast>
</wp:Notification>
"""
TILE_XML = """
<?xml version="1.0" encoding="utf-8"?>
<wp:Notification xmlns:wp="WPNotification">
    <wp:Tile>
        %s
        %s
        %s
        %s
        %s
        %s
    </wp:Tile>
</wp:Notification>
"""

class MPNSClient(PushService):
    def __init__(self, masterdb, app, instanceid=0):
        self.app = app
        self.masterdb = masterdb
    def process(self, **kwargs):
        url = kwargs['token']
        message = kwargs['alert']
        mpnsparams = kwargs['mpns']
        target = 'token'
        if 'target' in mpnsparams:
            target = mpnsparams['target']

        interval = 1
        if 'interval' in mpnsparams:
            interval = mpnsparams['interval']
        mpnstype = 'toast'
        if 'type' in mpnsparams:
            mpnstype = mpnsparams['type']

        logging.info(mpnsparams)
        if mpnstype == 'toast':
            text1 = message
            if 'text1' in mpnsparams:
                text1 = mpnsparams['text1']
            text2 = '';
            if 'text2' in mpnsparams:
                text2 = mpnsparams['text2']
            param = ''
            if 'param' in mpnsparams:
                param = "<wp:Param>%s</wp:Param>" % mpnsparams['param']
            xml = TOAST_XML % (str(text1), str(text2), str(param))
        elif mpnstype == 'tile':
            backgroundimage = ''
            if 'backgroundimage' in mpnsparams:
                backgroundimage = "<wp:BackgroundImage>%s</wp:BackgroundImage>" % mpnsparams['backgroundimage']
            count = 0
            if 'count' in mpnsparams:
                count = "<wp:Count>%s</wp:Count>" % mpnsparams['count']
            title = message
            if 'title' in mpnsparams:
                title = "<wp:Title>%s</wp:Title>" % mpnsparams['title']
            backbackgroundimage = ''
            if 'backbackgroundimage' in mpnsparams:
                backbackgroundimage = "<wp:BackBackgroundImage>%s</wp:BackBackgroundImage>" % mpnsparams['backbackgroundimage']
            backtitle = message
            if 'backtitle' in mpnsparams:
                backtitle = "<wp:BackTitle>%s</wp:BackTitle>" % mpnsparams['backtitle']
            backcontent = ''
            if 'backcontent' in mpnsparams:
                backcontent = "<wp:BackContent>%s</wp:BackContent>" % mpnsparams['backcontent']
            xml = TILE_XML % (backgroundimage, count, title, backbackgroundimage, backtitle, backcontent)

        logging.info(xml)
        headers = {
                'Content-Type': 'text/xml',
                'X-WindowsPhone-Target': target,
                'X-NotificationClass': interval,
                }
        response = requests.post(url, data=xml, headers=headers)
        if response.status_code != 200:
            logging.info('MPNS: something bad happened')
