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

from http.client import (
    BAD_REQUEST,
    LOCKED,
    FORBIDDEN,
    NOT_FOUND,
    INTERNAL_SERVER_ERROR,
    OK,
)
import binascii
import logging
import random
import time
import urllib.request, urllib.parse, urllib.error
import uuid
import requests
import tornado.web
from dao import Dao

from util import json_decode, json_encode
from constants import (
    DEVICE_TYPE_FCM,
    DEVICE_TYPE_IOS,
    DEVICE_TYPE_ANDROID,
    DEVICE_TYPE_WNS,
    RELEASE,
)
from bson.objectid import ObjectId
from hashlib import md5
from pushservices.wns import WNSInvalidPushTypeException
from routes import route
from tornado.options import options
from util import filter_alphabetanum, json_default, strip_tags

API_PERMISSIONS = {
    "create_token": (0b00001, "Create token"),
    "delete_token": (0b00010, "Delete token"),
    "send_notification": (0b00100, "Send notification"),
    "send_broadcast": (0b01000, "Send broadcast"),
    "create_accesskey": (0b10000, "Create access key"),
}


class APIBaseHandler(tornado.web.RequestHandler):
    """APIBaseHandler class to precess REST requests
    """

    def initialize(self):
        self.accesskeyrequired = True
        self._time_start = time.time()
        self.dao = self.application.container.dao

    def prepare(self):
        """Pre-process HTTP request
        """
        self.appname = None
        if "X-An-App-Name" in self.request.headers:
            self.appname = self.request.headers["X-An-App-Name"]
        else:
            self.send_response(BAD_REQUEST, dict(error="app name is required"))

        if not self.appname:
            self.appname = filter_alphabetanum(self.get_argument("appname"))

        self.dao.set_current_app(self.appname)

        self.appkey = None
        if "X-An-App-Key" in self.request.headers:
            self.appkey = self.request.headers["X-An-App-Key"]
        else:
            self.send_response(BAD_REQUEST, dict(error="app key is required"))

        self.token = self.get_argument("token", None)
        self.device = self.get_argument("device", DEVICE_TYPE_IOS).lower()
        if self.device == DEVICE_TYPE_IOS and self.token:
            if len(self.token) != 64:
                # hack until we resolve some bugs at the moodle side
                if len(self.token) > 64:
                    self.device = DEVICE_TYPE_ANDROID
                else:
                    self.send_response(BAD_REQUEST, dict(error="Invalid token"))
                    return
            else:
                try:
                    binascii.unhexlify(self.token)
                except Exception as ex:
                    self.send_response(BAD_REQUEST, dict(error="Invalid token"))
        else:
            # if it's not ios then we force android type device here
            self.device = DEVICE_TYPE_ANDROID

        self.app = self.dao.find_app_by_name(self.appname)

        if not self.app:
            self.send_response(BAD_REQUEST, dict(error="Invalid application name"))

        if not self.check_blockediplist(self.request.remote_ip, self.app):
            self.send_response(LOCKED, dict(error="Blocked IP"))
        else:
            key = self.db.keys.find_one({"key": self.appkey})
            if not key:
                self.permission = 0
                if self.accesskeyrequired:
                    self.send_response(BAD_REQUEST, dict(error="Invalid access key"))
            else:
                if "permission" not in key:
                    key["permission"] = 0
                self.permission = int(key["permission"])

    def can(self, permissionname):
        if permissionname not in API_PERMISSIONS:
            return False
        else:
            return (
                self.permission & API_PERMISSIONS[permissionname][0]
            ) == API_PERMISSIONS[permissionname][0]

    def check_blockediplist(self, ip, app):
        if "blockediplist" in app:
            from netaddr import IPNetwork, IPAddress

            iplist = app["blockediplist"].splitlines()
            for blockedip in iplist:
                if IPAddress(ip) in IPNetwork(blockedip):
                    return False
        return True

    @property
    def dbname(self):
        """ DB name"""
        return options.appprefix + self.appname

    @property
    def db(self):
        """ App DB, store logs/objects/users etc """
        return self.application.mongodb[self.dbname]

    @property
    def masterdb(self):
        """ Master DB instance, store airnotifier data """
        return self.application.masterdb

    @property
    def apnsconnections(self):
        """ APNs connections """
        return self.application.services["apns"]

    @property
    def fcmconnections(self):
        """ FCM connections """
        return self.application.services["fcm"]

    @property
    def wnsconnections(self):
        """ WNS connections """
        return self.application.services["wns"]

    @property
    def mpnsconnections(self):
        """ WNS connections """
        return self.application.services["mpns"]

    @property
    def smsconnections(self):
        """ WNS connections """
        return self.application.services["sms"]

    def set_default_headers(self):
        self.set_header("Content-Type", "application/json; charset=utf-8")

    def set_headers(self, headers):
        for name in headers:
            self.set_header(name, headers[name])

    def send_response(self, status_code=200, data=None, headers=None):
        """ Set REST API response """
        self.set_status(status_code, None)
        if headers is not None:
            self.set_headers(headers)
        if data:
            data = json_encode(data)
        else:
            data = ""

        self.finish(data)

    def finish(self, chunk=None):
        super(APIBaseHandler, self).finish(chunk)
        self._time_end = time.time()
        logging.info(
            "%s call ends %s" % (type(self).__name__, self._time_end - self._time_start)
        )

    def add_to_log(self, action, info=None, level="info"):
        log = {}
        log["action"] = strip_tags(action)
        log["info"] = strip_tags(info)
        log["level"] = strip_tags(level)
        log["created"] = int(time.time())
        self.db.logs.insert(log)


class EntityBuilder(object):
    @staticmethod
    def build_token(token, device, appname, channel, created=time.time()):
        tokenentity = {}
        tokenentity["device"] = device
        tokenentity["appname"] = appname
        tokenentity["token"] = token
        tokenentity["channel"] = channel
        tokenentity["created"] = created
        return tokenentity


@route(r"/tokens/([^/]+)")
class TokenV1Handler(APIBaseHandler):
    def delete(self, token):
        """Delete a token
        """
        # To check the access key permissions we use bitmask method.
        if not self.can("delete_token"):
            self.send_response(FORBIDDEN, dict(error="No permission to delete token"))
            return

        try:
            result = self.db.tokens.remove({"token": token})
            if result["n"] == 0:
                self.send_response(NOT_FOUND, dict(status="Token does't exist"))
            else:
                self.send_response(OK, dict(status="deleted"))
        except Exception as ex:
            self.send_response(INTERNAL_SERVER_ERROR, dict(error=str(ex)))

    def post(self, devicetoken):
        """Create a new token
        """
        if not self.can("create_token"):
            self.send_response(FORBIDDEN, dict(error="No permission to create token"))
            return

        device = self.get_argument("device", DEVICE_TYPE_FCM).lower()

        if device == DEVICE_TYPE_IOS and devicetoken:
            if len(devicetoken) != 64:
                # hack until we resolve some bugs at the moodle side
                if len(devicetoken) > 64:
                    device = DEVICE_TYPE_ANDROID
                else:
                    self.send_response(BAD_REQUEST, dict(error="Invalid token"))
                    return
            else:
                try:
                    binascii.unhexlify(devicetoken)
                except Exception as ex:
                    self.send_response(BAD_REQUEST, dict(error="Invalid token"))
        else:
            # if it's not ios then we force FCM type device here
            device = DEVICE_TYPE_FCM

        channel = self.get_argument("channel", "default")

        token = EntityBuilder.build_token(devicetoken, device, self.appname, channel)
        try:
            result = self.db.tokens.update(
                {"device": device, "token": devicetoken, "appname": self.appname},
                token,
                upsert=True,
            )
            # result
            # {u'updatedExisting': True, u'connectionId': 47, u'ok': 1.0, u'err': None, u'n': 1}
            if result["updatedExisting"]:
                self.send_response(OK, dict(status="token exists"))
            else:
                self.send_response(OK, dict(status="ok"))
                self.add_to_log("Add token", devicetoken)
        except Exception as ex:
            self.add_to_log("Cannot add token", devicetoken, "warning")
            self.send_response(INTERNAL_SERVER_ERROR, dict(error=str(ex)))


@route(r"/users")
@route(r"/api/v2/users")
class UsersHandler(APIBaseHandler):
    """Handle users
    - Take application ID and secret
    - Create user
    """

    def post(self):
        """Register user
        """
        password = self.get_argument("password")
        email = self.get_argument("email")
        now = int(time.time())
        user = {"password": password, "email": email, "created": now}
        try:
            cursor = self.db.users.find_one({"email": email})
            if cursor:
                self.send_response(BAD_REQUEST, dict(error="email already exists"))
            else:
                userid = self.db.users.insert(user)
                self.add_to_log("Add user", email)
                self.send_response(OK, {"userid": str(userid)})
        except Exception as ex:
            self.send_response(INTERNAL_SERVER_ERROR, dict(error=str(ex)))

    def get(self):
        """Query users
        """
        where = self.get_argument("where", None)
        if not where:
            data = {}
        else:
            try:
                # unpack query conditions
                data = json_decode(where)
            except Exception as ex:
                self.send_response(BAD_REQUEST, dict(error=str(ex)))

        cursor = self.db.users.find(data)
        users = []
        for u in cursor:
            users.append(u)
        self.send_response(OK, users)


@route(r"/objects/([^/]+)/([^/]+)")
@route(r"/api/v2/objects/([^/]+)/([^/]+)")
class ObjectHandler(APIBaseHandler):
    """Object Handler
    http://airnotifier.xxx/objects/cars/4f794f7329ddda1cb9000000
    """

    def get(self, classname, objectId):
        """Get object by ID
        """
        self.classname = classname
        self.objectid = ObjectId(objectId)
        doc = self.db[self.collection].find_one({"_id": self.objectid})
        self.send_response(OK, doc)
        return

    def delete(self, classname, objectId):
        """Delete a object
        """
        self.classname = classname
        self.objectid = ObjectId(objectId)
        result = self.db[self.collection].remove({"_id": self.objectid})
        self.send_response(OK, dict(result=result))

    def put(self, classname, objectId):
        """Update a object
        """
        self.classname = classname
        data = json_decode(self.request.body)
        self.objectid = ObjectId(objectId)
        result = self.db[self.collection].update({"_id": self.objectid}, data)

    @property
    def collection(self):
        collectionname = "%s%s" % (options.collectionprefix, self.classname)
        return collectionname


@route(r"/objects/([^/]+)")
@route(r"/api/v2/objects/([^/]+)")
class ClassHandler(APIBaseHandler):
    """Object Handler
    http://airnotifier.xxx/objects/cars
    """

    @property
    def collection(self):
        cursor = self.db.objects.find_one({"collection": self.classname})
        if not cursor:
            col = {}
            col["collection"] = self.classname
            col["created"] = int(time.time())
            self.add_to_log("Register collection", self.classname)
            self.db.objects.insert(col)

        collectionname = "%s%s" % (options.collectionprefix, self.classname)
        return collectionname

    def get(self, classname):
        """Query collection
        """
        self.classname = classname
        where = self.get_argument("where", None)
        if not where:
            data = {}
        else:
            try:
                # unpack query conditions
                data = json_decode(where)
            except Exception as ex:
                self.send_response(BAD_REQUEST, dict(error=str(ex)))

        objects = self.db[self.collection].find(data)
        results = []
        for obj in objects:
            results.append(obj)
        self.send_response(OK, results)

    def post(self, classname):
        """Create collections
        """
        self.classname = classname
        try:
            data = json_decode(self.request.body)
        except Exception as ex:
            self.send_response(BAD_REQUEST, ex)

        self.add_to_log("Add object to %s" % self.classname, data)
        objectId = self.db[self.collection].insert(data)
        self.send_response(OK, dict(objectId=objectId))


@route(r"/accesskeys/")
class AccessKeysV1Handler(APIBaseHandler):
    def initialize(self):
        self.accesskeyrequired = False
        self._time_start = time.time()

    def post(self):
        """Create access key
        """
        result = self.verify_request()
        if not result:
            self.send_response(
                FORBIDDEN, dict(error="Site not registered on moodle.net")
            )
            return
        key = {}
        key["contact"] = self.get_argument("contact", "")
        key["description"] = self.get_argument("description", "")
        key["created"] = int(time.time())
        # This is 1111 in binary means all permissions are granted
        key["permission"] = (
            API_PERMISSIONS["create_token"][0]
            | API_PERMISSIONS["delete_token"][0]
            | API_PERMISSIONS["send_notification"][0]
            | API_PERMISSIONS["send_broadcast"][0]
        )
        key["key"] = md5(str(uuid.uuid4())).hexdigest()
        self.db.keys.insert(key)
        self.send_response(OK, dict(accesskey=key["key"]))

    def verify_request(self):
        huburl = "https://moodle.net/local/sitecheck/check.php"
        mdlurl = self.get_argument("url", "")
        mdlsiteid = self.get_argument("siteid", "")
        params = {"siteid": mdlsiteid, "url": mdlurl}
        response = requests.get(huburl, params=params)
        result = int(response.text)
        if result == 0:
            return False
        else:
            return True


@route(r"/broadcast/")
class BroadcastV1Handler(APIBaseHandler):
    def post(self):
        if not self.can("send_broadcast"):
            self.send_response(FORBIDDEN, dict(error="No permission to send broadcast"))
            return

        # the channel to be broadcasted
        channel = self.get_argument("channel", "default")
        # iOS and Android shared params
        alert = "".join(self.get_argument("alert").splitlines())
        # Android
        collapse_key = self.get_argument("collapse_key", "")
        # iOS
        sound = self.get_argument("sound", None)
        badge = self.get_argument("badge", None)
        self.add_to_log("%s broadcast" % self.appname, alert, "important")
        self.application.send_broadcast(self.appname, self.db, channel, alert)
        delta_t = time.time() - self._time_start
        logging.info("Broadcast took time: %sms" % (delta_t * 1000))
        self.send_response(OK, dict(status="ok"))
