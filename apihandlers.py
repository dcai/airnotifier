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
# MongoDB
from pymongo import *
from bson import *

class APIBaseHandler(tornado.web.RequestHandler):
    """APIBaseHandler class to precess REST requests
    """
    def initialize(self):
        pass

    def prepare(self):
        """Pre-process HTTP request
        """

        if self.request.headers.has_key('X-An-App-Name'):
            """ App name """
            self.appname = self.request.headers['X-An-App-Name'];

        if self.request.headers.has_key('X-An-App-Key'):
            """ App key """
            self.appkey = self.request.headers['X-An-App-Key']

        if not self.appname:
            self.appname = self.get_argument('appname')

        self.token = self.get_argument('token', None)
        if self.token:
            if len(self.token) != 64:
                self.send_response(dict(error='Invalid token'))

        self.app = self.masterdb.applications.find_one({'shortname': self.appname})
        key = self.db.keys.find_one({'key':self.appkey})
        if not key:
            self.send_response(dict(error='Invalid Key'))
        if not self.app:
            self.send_response(dict(error='Invalid Application Name'))

    @property
    def db(self):
        """ DB instance """
        return self.application.mongodb[self.appname]

    @property
    def masterdb(self):
        return self.application.masterdb

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
        try:
            result = self.db.tokens.remove({'token':token}, True)
            logging.info(result)
            if result['n'] == 0:
                self.send_response(dict(status='Token does\'t exist'))
            else:
                self.send_response(dict(status='deleted'))
        except Exception, ex:
            self.send_response(dict(error=str(ex)))

    def post(self, token):
        """Create a new token
        """
        record = self.db.tokens.find_one({'token': token})
        if record and record.has_key('token'):
            self.send_response(dict(error="Token already recorded"))
        else:
            now = int(time.time())
            token = {
                    'appname': self.appname,
                    'token': token,
                    'created': now,
                    }
            try:
                result = self.db.tokens.insert(token)
                self.send_response(dict(status='ok'))
            except Exception, ex:
                self.send_response(dict(error=str(ex)))

class NotificationHandler(APIBaseHandler):

    def post(self):
        """ Send notifications """
        if not self.token:
            self.send_response(dict(error="No token provided"))

        token = self.db.tokens.find_one({'token': self.token})
        if not token:
            now = int(time.time())
            token = {
                    'appname': self.appname,
                    'token': self.token,
                    'created': now,
                    }
            logging.info(token)
            try:
                result = self.db.tokens.insert(token)
            except Exception, ex:
                self.send_response(dict(error=str(ex)))

        alert = self.get_argument('alert')
        sound = self.get_argument('sound', 'default')
        badge = int(self.get_argument('badge', 0))
        pl = PayLoad(alert=alert, sound=sound, badge=1)
        count = len(self.apnsconnections[self.app['shortname']])
        random.seed(time.time())
        instanceid = random.randint(0, count-1)
        conn = self.apnsconnections[self.app['shortname']][instanceid]
        try:
            conn.send(self.token, pl)
            self.send_response(dict(status='ok'))
        except Exception, ex:
            self.send_response(dict(error=str(ex)))

class UsersHandler(APIBaseHandler):
    """Handle users
    - Take application ID and secret
    - Create user
    """
    def post(self):
        """Register user
        """
        username = self.get_argument('username')
        password = self.get_argument('password')
        email = self.get_argument('email')
        now = int(time.time())
        user = {
                'username': username,
                'password': password,
                'email': email,
                'created': now,
        }
        try:
            user = self.db.users.find_one({'username':username})
            if user:
                self.send_response(dict(error='Username already exists'))
            else:
                userid = self.db.users.insert(user)
                self.send_response({'userid': userid})
        except Exception, ex:
            self.send_response(dict(error=str(ex)))

    def get(self):
        """Query users
        """
        cursor = self.db.users.find()
        users = []
        for u in cursor:
            users.append(u)
        self.send_response(users)

class UserHandler(APIBaseHandler):
    def delete(self, userId):
        """ Delete user """
        pass

    def put(self, userId):
        """ Update """
        pass

    def get(self, userId):
        """Get user details by ID
        """
        username = self.get_argument('username', None)
        email = self.get_argument('email', None)
        userid = self.get_argument('userid', None)
        conditions = {}
        if username:
            conditions['username'] = username
        if email:
            conditions['email'] = email
        if userid:
            conditions['id'] = userid


class ObjectHandler(APIBaseHandler):
    """Object Handler
    http://airnotifier.xxx/objects/option/1
    option will be the resource name
    """
    def get(self, classname, objectId):
        """Get object by ID
        """
        self.objectid = ObjectId(objectId)
        doc = self.db[classname].find_one({'_id': self.objectid})
        doc['_id'] = str(doc['_id'])
        self.send_response(doc)

    def delete(self, classname, objectId):
        """Delete a object
        """
        self.objectid = ObjectId(objectId)
        result = self.db[classname].remove({'_id': self.objectid}, True)
        self.send_response(dict(result=result))

    def put(self, classname, objectId):
        """Update a object
        """
        data = json.loads(self.request.body)
        self.objectid = ObjectId(objectId)
        result = self.db[classname].update({'_id': self.objectid}, data)

class ClassHandler(APIBaseHandler):
    """Object Handler
    http://airnotifier.xxx/objects/option/1
    option will be the resource name
    """
    def get(self, classname):
        """Query collection
        """
        objects = self.db[classname].find()
        results = []
        for obj in objects:
            obj['_id'] = str(obj['_id'])
            results.append(obj)
        logging.info(results)
        self.send_response(results)

    def post(self, classname):
        """Create entry
        """
        data = json.loads(self.request.body)
        objectId = self.db[classname].insert(data)
        self.send_response(dict(objectId=str(objectId)))

class FilesHandler(APIBaseHandler):
    def post(self):
        ## hash and store a file
        pass
