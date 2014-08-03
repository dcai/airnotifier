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

from hashlib import md5, sha1
from routes import route
from tornado.options import options
import logging
import os
import platform
import random
import tornado.web
from bson.objectid import ObjectId
import time
import uuid
from constants import DEVICE_TYPE_IOS, VERSION
from pymongo import DESCENDING
from util import filter_alphabetanum
from pushservices.apns import APNClient, APNFeedback, PayLoad
import sys
from api import API_PERMISSIONS
from pushservices.gcm import GCMException
from pushservices.wns import WNSClient
from pushservices.gcm import GCMClient
import requests
from controllers.base import *

@route(r"/applications/([^/]+)/broadcast")
class AppBroadcastHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)
        self.render("app_broadcast.html", app=app, sent=False)
    @tornado.web.authenticated
    def post(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)
        alert = self.get_argument('notification').strip()
        sound = 'default'
        count = len(self.apnsconnections[app['shortname']])
        if appname in self.apnsconnections:
            count = len(self.apnsconnections[appname])
        else:
            count = 0
        if count > 0:
            random.seed(time.time())
            instanceid = random.randint(0, count - 1)
            conn = self.apnsconnections[appname][instanceid]
        else:
            conn = None
        regids = []

        tokens = self.db.tokens.find()
        try:
            for token in tokens:
                if token['device'] == DEVICE_TYPE_IOS:
                    if conn is not None:
                        pl = PayLoad(alert=alert, sound=sound)
                        conn.send(token['token'], pl)
                else:
                    regids.append(token['token'])
        except Exception:
            pass
        try:
            # Now sending android notifications
            gcm = self.gcmconnections[appname][0]
            data = dict({'alert': alert}.items())
            response = gcm.send(regids, data=data, ttl=3600)
            responsedata = response.json()
        except GCMException:
            logging.error('GCM problem')
        self.render("app_broadcast.html", app=app, sent=True)

