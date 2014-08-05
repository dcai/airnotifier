#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2012, Dongsheng Cai
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the Dongsheng Cai nor the names of its
#      contributors may be used to endorse or promote products derived
#      from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL DONGSHENG CAI BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from . import PushService
import requests
import logging
import time

class WNSException(Exception): pass

class WNSInvalidPushTypeException(WNSException):
    def __init__(self, type):
        Exception.__init__(self, "WNS Invalid push notification type :" + type)

WNSACCESSTOKEN_URL = 'https://login.live.com/accesstoken.srf'
TOAST_XML = """
<toast>
    <visual>
        <binding template="%s">
        %s %s
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
        wnstype = wnsparams.get('type', 'toast')

        if wnstype not in ['toast', 'tile', 'badge', 'raw']:
            raise WNSInvalidPushTypeException(wnstype)

        if wnstype == 'toast':
            template = wnsparams.get('template', 'ToastText01')
            text = ""
            if 'text' in wnsparams:
                count = 1
                for t in wnsparams['text']:
                    text = text + '<text id="%d">%s</text>' % (count, t)
                    count = count + 1
            image = ''
            if 'image' in wnsparams:
                count = 1
                for img in wnsparams['image']:
                    image = image + '<img id="%d" src="%s" />' % (count, img)
                    count = count + 1
            xml = TOAST_XML % (template, image, text)
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
                    raise WNSInvalidPushTypeException('tile')
            else:
                raise WNSInvalidPushTypeException('tile')
        elif wnstype == 'badge':
            if 'badge' in wnsparams:
                if 'value' in wnsparams['badge']:
                    badgevalue = wnsparams['badge']['value']
                    xml = BADGE_XML % badgevalue
                else:
                    raise WNSInvalidPushTypeException('badge')
            else:
                raise WNSInvalidPushTypeException('badge')
        else:
            raise WNSInvalidPushTypeException(wnstype)

        wnstype = 'wns/' + wnstype

        accesstoken = self.accesstoken
        if self.expiry >= now:
            accesstoken = self.request_token()
        headers = {
                'Content-Type': 'text/xml',
                'X-WNS-Type': wnstype,
                'Authorization': 'Bearer %s' % (accesstoken),
                }
        response = requests.post(url, data=xml, headers=headers)
        if response.status_code == 400:
            raise WNSException('WNS 400 Bad Request: One or more headers were specified incorrectly')
        elif response.status_code == 401:
            raise WNSException('WNS 401 Unauthorized: The cloud service did not present a valid authentication ticket. The OAuth ticket may be invalid.')
        elif response.status_code >= 500:
            raise WNSEsception('WNS ' + response.status_code + ' Service issue')
        else:
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
