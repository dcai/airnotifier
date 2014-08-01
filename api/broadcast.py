#!/usr/bin/python
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

from httplib import BAD_REQUEST, LOCKED, FORBIDDEN, NOT_FOUND, \
    INTERNAL_SERVER_ERROR, OK, ACCEPTED
from routes import route
from api import APIBaseHandler
import random
import time
from constants import DEVICE_TYPE_IOS
from pushservices.apns import PayLoad
from pushservices.gcm import GCMException
import logging

@route(r"/broadcast/")
@route(r"/api/v2/broadcast/")
class BroadcastHandler(APIBaseHandler):
    def post(self):
        if not self.can('send_broadcast'):
            self.send_response(FORBIDDEN, dict(error="No permission to send broadcast"))
            return

        # the cannel to be boradcasted
        channel = self.get_argument('channel', 'default')
        # iOS and Android shared params
        alert = ''.join(self.get_argument('alert').splitlines())
        # Android
        collapse_key = self.get_argument('collapse_key', '')
        # iOS
        sound = self.get_argument('sound', None)
        badge = self.get_argument('badge', None)

        conditions = []
        if channel == 'default':
            # channel is not set or channel is default
            conditions.append({'channel': {"$exists": False}})
            conditions.append({'channel': 'default'})
        else:
            conditions.append({'channel': channel})
        tokens = self.db.tokens.find({"$or": conditions})

        knownparams = ['alert', 'sound', 'badge', 'token', 'device', 'collapse_key']
        # Build the custom params  (everything not alert/sound/badge/token)
        customparams = {}
        allparams = {}
        for name, value in self.request.arguments.items():
            allparams[name] = self.get_argument(name)
            if name not in knownparams:
                customparams[name] = self.get_argument(name)

        self.add_to_log('%s broadcast' % self.appname, alert, "important")
        if self.app['shortname'] in self.apnsconnections:
            count = len(self.apnsconnections[self.app['shortname']])
        else:
            count = 0
        if count > 0:
            random.seed(time.time())
            instanceid = random.randint(0, count - 1)
            conn = self.apnsconnections[self.app['shortname']][instanceid]
        else:
            conn = None
        regids = []
        try:
            for token in tokens:
                if token['device'] == DEVICE_TYPE_IOS:
                    if conn is not None:
                        pl = PayLoad(alert=alert, sound=sound, badge=badge, identifier=0, expiry=None, customparams=customparams)
                        conn.send(token['token'], pl)
                else:
                    regids.append(token['token'])
        except Exception:
            pass

        try:
            # Now sending android notifications
            gcm = self.gcmconnections[self.app['shortname']][0]
            data = dict({'alert': alert}.items() + customparams.items())
            response = gcm.send(regids, data=data, collapse_key=collapse_key, ttl=3600)
            responsedata = response.json()
        except GCMException:
            logging.info('GCM problem')

        delta_t = time.time() - self._time_start
        logging.warning("Broadcast took time: %sms" % (delta_t * 1000))
        self.send_response(OK, dict(status='ok'))
