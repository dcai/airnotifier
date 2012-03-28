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

import tornado.database
import tornado.web
import random
## APNs library
from apns import *

class APIBaseHandler(tornado.web.RequestHandler):
    """APIBaseHandler class to precess REST requests
    """
    def initialize(self):
        pass

    def prepare(self):
        """Pre-process HTTP request
        """
        """ Parsing application ID and KEY """
        if self.request.headers.has_key('X-An-App-Key'):
            self.appkey = self.request.headers['X-An-App-Key']

        if self.request.headers.has_key('X-An-App-Id'):
            """ This is an int value """
            self.appid = int(self.request.headers['X-An-App-Id']);

        if not self.appid:
            self.appid = self.get_argument('appid')

        self.token = self.get_argument('token', None)
        if self.token:
            if len(self.token) != 64:
                self.send_response(dict(error='Invalid token'))

        self.app = self.db.get("SELECT app.id, app.shortname FROM applications app WHERE app.id=%s", self.appid)
        if not self.app:
            self.send_response(dict(error='Invalid app ID'))

    @property
    def db(self):
        """ DB instance """
        return self.application.db

    @property
    def apnsconnections(self):
        """ APNs connections"""
        return self.application.apnsconnections

    def send_response(self, data=None, headers=None):
        """ Set REST API response """

        self.set_header('Content-Type', 'application/json; charset=utf-8')
        self.set_header('X-Powered-By', 'AirNotifier/1.0')
        if data:
            jsontext = json.dumps(data)
            self.finish(jsontext)
        else:
            self.finish()

class TokenHandler(APIBaseHandler):
    def delete(self, token):
        """Delete a token
        """
        sql = "DELETE FROM tokens WHERE appid=%s AND token=%s"
        try:
            result = self.db.execute(sql, self.appid, token)
            self.send_response(dict(status='ok'))
        except Exception, ex:
            self.send_response(dict(error=str(ex)))

    def post(self, token):
        """Create a new token
        """
        sql = "INSERT INTO tokens (appid, token, created) VALUES (%s, %s, %s)"
        now = int(time.time())
        try:
            result = self.db.execute(sql, self.appid, token, now)
            self.send_response(dict(status='ok'))
        except Exception, ex:
            self.send_response(dict(error=str(ex)))

class NotificationHandler(APIBaseHandler):

    def get(self):
        """ For testing only """
        pass

    def post(self):

        alert = self.get_argument('alert')
        sound = self.get_argument('sound', 'default')
        badge = int(self.get_argument('badge', 0))
        pl = PayLoad(alert=alert, sound=sound, badge=1)
        count = len(self.apnsconnections[self.app.shortname])
        random.seed(time.time())
        instanceid = random.randint(0, count-1)
        conn = self.apnsconnections[self.app.shortname][instanceid]
        try:
            conn.send(self.token, pl)
            self.send_response(dict(status='ok'))
        except Exception, ex:
            self.send_response(dict(error=str(ex)))

class UserHandler(APIBaseHandler):
    """Handle users
    - Take application ID and secret
    - Create user
    """
    def post(self):
        """ Create user """
        pass
    def get(self):
        """Get user info
        supply loggged token to get private info
        """
        pass
    def delete(self):
        """ Delete user """
        pass
    def put(self):
        """ Update """
        pass

class ObjectHandler(APIBaseHandler):
    """Object Handler
    http://airnotifier.xxx/objects/option/1
    option will be the resource name
    """
    def get(self):
        """Query resource
        """
        pass
    def post(self):
        """Create object
        """
        pass
