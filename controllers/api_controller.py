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

from apns import *
from bson import *
from pymongo import *
from routes import route
from tornado.options import define, options
from util import *
import urllib
import urllib2
import binascii
from hashlib import md5, sha1
import random
import time
import tornado.web

class APIBaseHandler(tornado.web.RequestHandler):
    """APIBaseHandler class to precess REST requests
    """
    def initialize(self):
        self.accesskeyrequired = True
        self._time_start = time.time()

    def prepare(self):
        """Pre-process HTTP request
        """
        if self.request.headers.has_key('X-An-App-Name'):
            """ App name """
            self.appname = self.request.headers['X-An-App-Name'];

        if not self.appname:
            self.appname = filter_alphabetanum(self.get_argument('appname'))

        if self.request.headers.has_key('X-An-App-Key'):
            """ App key """
            self.appkey = self.request.headers['X-An-App-Key']

        self.token = self.get_argument('token', None)
        if self.token:
            # If token provided, it must be 64 chars
            if len(self.token) != 64:
                self.send_response(dict(error='Invalid token'))
            try:
                value = binascii.unhexlify(self.token)
            except Exception, ex:
                self.send_response(dict(error='Invalid token'))

        self.app = self.masterdb.applications.find_one({'shortname': self.appname})

        if not self.app:
            self.send_response(dict(error='Invalid application name'))

        if not self.check_blockediplist(self.request.remote_ip, self.app):
            self.send_response(dict(error='Blocked IP'))
        else:

            key = self.db.keys.find_one({'key':self.appkey})
            if not key:
                self.permission = 0
                if self.accesskeyrequired:
                    self.send_response(dict(error='Invalid access key'))
            else:
                if 'permission' not in key:
                    key['permission'] = 0
                self.permission = int(key['permission'])

    def check_blockediplist(self, ip, app):
        if app.has_key('blockediplist') and app['blockediplist']:
            from netaddr import IPNetwork, IPAddress
            iplist = app['blockediplist'].splitlines()
            for blockedip in iplist:
                if IPAddress(ip) in IPNetwork(blockedip):
                    return False
        return True

    @property
    def db(self):
        """ App DB, store logs/objects/users etc """
        return self.application.mongodb[self.appname]

    @property
    def masterdb(self):
        """ Master DB instance, store airnotifier data """
        return self.application.masterdb

    @property
    def apnsconnections(self):
        """ APNs connections """
        return self.application.apnsconnections

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json; charset=utf-8')
        self.set_header('X-Powered-By', 'AirNotifier/1.0')

    def send_response(self, data=None, headers=None):
        """ Set REST API response """
        if data:
            data = json.dumps(data, default=json_default)
        else:
            data = None

        self.finish(data)

    def finish(self, chunk=None):
        super(APIBaseHandler, self).finish(chunk)
        self._time_end = time.time()

    def add_to_log(self, action, info=None, level="info"):
        log = {}
        log['action'] = action
        log['info'] = info
        log['level'] = level
        log['created'] = int(time.time())
        self.db.logs.insert(log, safe=True)

@route(r"/tokens/([^/]+)")
class TokenHandler(APIBaseHandler):
    def delete(self, token):
        """Delete a token
        """
        # To check the access key permissions we use bitmask method.
        if (self.permission & 2) != 2:
            self.send_response(dict(error="No permission to delete token"))
            return

        try:
            result = self.db.tokens.remove({'token':token}, safe=True)
            if result['n'] == 0:
                self.send_response(dict(status='Token does\'t exist'))
            else:
                self.send_response(dict(status='deleted'))
        except Exception, ex:
            self.send_response(dict(error=str(ex)))

    def post(self, devicetoken):
        """Create a new token
        """
        if (self.permission & 1) != 1:
            self.send_response(dict(error="No permission to create token"))
            return

        if len(devicetoken) != 64:
            self.send_response(dict(error='Invalid token'))
            return

        try:
            value = binascii.unhexlify(devicetoken)
        except Exception, ex:
            self.send_response(dict(error='Invalid token'))

        channel = self.get_argument('channel', 'default')

        now = int(time.time())
        token = {
            'appname': self.appname,
            'token': devicetoken,
            'channel': channel,
        }
        try:
            result = self.db.tokens.update({'token': devicetoken, 'appname': self.appname}, token, safe=True, upsert=True)
            # result
            # {u'updatedExisting': True, u'connectionId': 47, u'ok': 1.0, u'err': None, u'n': 1}
            if result['updatedExisting']:
                self.send_response(dict(status='token exists'))
                self.add_to_log('Token exists', devicetoken)
            else:
                self.send_response(dict(status='ok'))
                self.add_to_log('Add token', devicetoken)
        except Exception, ex:
            self.add_to_log('Cannot add token', devicetoken, "warning")
            self.send_response(dict(error=str(ex)))

@route(r"/broadcast/")
class BroadcastHandler(APIBaseHandler):
    def post(self):
        if (self.permission & 8) != 8:
            self.send_response(dict(error="No permission to send broadcast"))
            return

        # the cannel to be boradcasted
        channel = self.get_argument('channel', 'default')

        # Message payload
        alert = self.get_argument('alert')
        sound = self.get_argument('sound', None)
        badge = self.get_argument('badge', None)
        if channel == 'default':
            # channel is not set or channel is default
            conditions = []
            conditions.append({'channel': {"$exists": False}})
            conditions.append({'channel': 'default'})
            tokens = self.db.tokens.find({"$or": conditions})
        else:
            tokens = self.db.tokens.find()

        # Build the custom params (everything not alert/sound/badge/channel)
        customparams = {}
        for paramname, param in self.request.arguments.iteritems():
            if paramname != 'alert' and paramname != 'sound' and paramname != 'badge' and paramname != 'channel':
                customparams[paramname] = param

        pl = PayLoad(alert=alert, sound=sound, badge=badge, identifier=0, expiry=None, customparams=customparams)

        self.add_to_log('%s broadcast' % self.appname, alert, "important")
        count = len(self.apnsconnections[self.app['shortname']])
        random.seed(time.time())
        instanceid = random.randint(0, count - 1)
        conn = self.apnsconnections[self.app['shortname']][instanceid]
        try:
            for token in tokens:
                conn.send(token['token'], pl)
        except Exception, ex:
            pass
        delta_t = time.time() - self._time_start
        logging.warning("Broadcast took time: %sms" % (delta_t * 1000))
        self.send_response(dict(status='ok'))

@route(r"/notification/")
class NotificationHandler(APIBaseHandler):
    def post(self):
        """ Send notifications """
        if (self.permission & 4) != 4:
            self.send_response(dict(error="No permission to send notification"))
            return

        if not self.token:
            self.send_response(dict(error="No token provided"))
            return

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
                result = self.db.tokens.insert(token, safe=True)
            except Exception, ex:
                self.send_response(dict(error=str(ex)))

        alert = self.get_argument('alert')
        sound = self.get_argument('sound', None)
        badge = self.get_argument('badge', None)
        # Build the custom params  (everything not alert/sound/badge/token)
        customparams = {}
        for paramname, param in self.request.arguments.items():
            if paramname != 'alert' and paramname != 'sound' and paramname != 'badge' and paramname != 'token':
                customparams[paramname] = self.get_argument(paramname)
        pl = PayLoad(alert=alert, sound=sound, badge=badge, identifier=0, expiry=None, customparams=customparams)
        if not self.apnsconnections.has_key(self.app['shortname']):
            # TODO: add message to queue in MongoDB
            self.send_response(dict(error="APNs is offline"))
            return
        count = len(self.apnsconnections[self.app['shortname']])
        random.seed(time.time())
        instanceid = random.randint(0, count - 1)
        conn = self.apnsconnections[self.app['shortname']][instanceid]
        try:
            self.add_to_log('%s notification' % self.appname, alert)
            conn.send(self.token, pl)
            self.send_response(dict(status='ok'))
        except Exception, ex:
            self.send_response(dict(error=str(ex)))

@route(r"/users")
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
            cursor = self.db.users.find_one({'username':username})
            if cursor:
                self.send_response(dict(error='Username already exists'))
            else:
                userid = self.db.users.insert(user, safe=True)
                self.add_to_log('Add user', username)
                self.send_response({'userid': str(userid)})
        except Exception, ex:
            self.send_response(dict(error=str(ex)))

    def get(self):
        """Query users
        """
        where = self.get_argument('where', None)
        if not where:
            data = {}
        else:
            try:
                # unpack query conditions
                data = json.loads(where)
            except Exception, ex:
                self.send_response(dict(error=str(ex)))

        cursor = self.db.users.find(data)
        users = []
        for u in cursor:
            users.append(u)
        self.send_response(users)

@route(r"/users/([^/]+)")
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


@route(r"/objects/([^/]+)/([^/]+)")
class ObjectHandler(APIBaseHandler):
    """Object Handler
    http://airnotifier.xxx/objects/cars/4f794f7329ddda1cb9000000
    """
    def get(self, classname, objectId):
        """Get object by ID
        """
        self.classname = classname
        self.objectid = ObjectId(objectId)
        doc = self.db[self.collection].find_one({'_id': self.objectid})
        self.send_response(doc)
        return

    def delete(self, classname, objectId):
        """Delete a object
        """
        self.classname = classname
        self.objectid = ObjectId(objectId)
        result = self.db[self.collection].remove({'_id': self.objectid}, safe=True)
        self.send_response(dict(result=result))

    def put(self, classname, objectId):
        """Update a object
        """
        self.classname = classname
        data = json.loads(self.request.body)
        self.objectid = ObjectId(objectId)
        result = self.db[self.collection].update({'_id': self.objectid}, data, safe=True)

    @property
    def collection(self):
        collectionname = "%s%s" % (options.dbprefix, self.classname)
        return collectionname

@route(r"/objects/([^/]+)")
class ClassHandler(APIBaseHandler):
    """Object Handler
    http://airnotifier.xxx/objects/cars
    """
    @property
    def collection(self):
        cursor = self.db.objects.find_one({'collection':self.classname})
        if not cursor:
            col = {}
            col['collection'] = self.classname
            col['created'] = int(time.time())
            self.add_to_log('Register collection', self.classname)
            self.db.objects.insert(col, safe=True)

        collectionname = "%s%s" % (options.dbprefix, self.classname)
        return collectionname

    def get(self, classname):
        """Query collection
        """
        self.classname = classname
        where = self.get_argument('where', None)
        if not where:
            data = {}
        else:
            try:
                # unpack query conditions
                data = json.loads(where)
            except Exception, ex:
                self.send_response(dict(error=str(ex)))

        objects = self.db[self.collection].find(data)
        results = []
        for obj in objects:
            results.append(obj)
        self.send_response(results)

    def post(self, classname):
        """Create collections
        """
        self.classname = classname
        try:
            data = json.loads(self.request.body)
        except Exception, ex:
            self.send_response(ex)

        self.add_to_log('Add object to %s' % self.classname, data)
        objectId = self.db[self.collection].insert(data, safe=True)
        self.send_response(dict(objectId=objectId))

@route(r"/accesskeys/")
class AccessKeysHandler(APIBaseHandler):
    def initialize(self):
        self.accesskeyrequired = False
        self._time_start = time.time()
    def post(self):
        """Create access key
        """
        key = {}
        key['contact'] = self.get_argument('contact', '')
        key['description'] = self.get_argument('description', '')
        key['created'] = int(time.time())
        # This is 1111 in binary means all permissions are granted
        key['permission'] = 15
        key['key'] = md5(str(uuid.uuid4())).hexdigest()
        keyObjectId = self.db.keys.insert(key)
        result = self.verify_request()
        if result:
            self.send_response(dict(accesskey=key['key']))
        else:
            self.send_response("Site not registered on moodle.net")

    def verify_request(self):
        huburl = "http://moodle.net/local/sitecheck/check.php"
        mdlurl = self.get_argument('url', '')
        mdlsiteid = self.get_argument('siteid', '')
        data = {
                'siteid': mdlsiteid,
                'url': mdlurl
                }
        postdata = urllib.urlencode(data)
        request = urllib2.Request(huburl, postdata)
        response = urllib2.urlopen(request)
        result = int(response.read())
        if result == 0:
            return False
        else:
            return True


@route(r"/files")
class FilesHandler(APIBaseHandler):
    def post(self):
        # hash and store a file
        pass
