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

try:
    from httplib import (
        BAD_REQUEST,
        LOCKED,
        FORBIDDEN,
        NOT_FOUND,
        INTERNAL_SERVER_ERROR,
        OK,
    )
except:
    from http.client import (
        BAD_REQUEST,
        LOCKED,
        FORBIDDEN,
        NOT_FOUND,
        INTERNAL_SERVER_ERROR,
        OK,
    )
import binascii
import json
import logging
import random
import time
import urllib
import uuid
import requests
import tornado.web

from constants import (
    DEVICE_TYPE_IOS,
    DEVICE_TYPE_ANDROID,
    DEVICE_TYPE_WNS,
    DEVICE_TYPE_MPNS,
)
from pushservices.apns import PayLoad
from pushservices.gcm import (
    GCMException,
    GCMInvalidRegistrationException,
    GCMNotRegisteredException,
    GCMUpdateRegIDsException,
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

_logger = logging.getLogger("api")


class APIBaseHandler(tornado.web.RequestHandler):
    """APIBaseHandler class to precess REST requests
    """

    def initialize(self):
        self.accesskeyrequired = True
        self._time_start = time.time()

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

        self.appkey = None
        if "X-An-App-Key" in self.request.headers:
            self.appkey = self.request.headers["X-An-App-Key"]
        else:
            self.send_response(BAD_REQUEST, dict(error="app key is required"))

        self.token = self.get_argument("token", None)
        self.device = self.get_argument("device", DEVICE_TYPE_IOS).lower()
        if self.device == DEVICE_TYPE_IOS:
            if self.token:
                # If token provided, it must be 64 chars
                if len(self.token) != 64:
                    self.send_response(BAD_REQUEST, dict(error="Invalid token"))
                try:
                    # Validate token
                    binascii.unhexlify(self.token)
                except Exception as ex:
                    self.send_response(
                        BAD_REQUEST, dict(error="Invalid token: %s" % ex)
                    )
        else:
            self.device = DEVICE_TYPE_ANDROID

        self.app = self.masterdb.applications.find_one({"shortname": self.appname})

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
        if app.has_key("blockediplist") and app["blockediplist"]:
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
    def gcmconnections(self):
        """ GCM connections """
        return self.application.services["gcm"]

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
        self.set_header("X-Powered-By", "AirNotifier/1.0")

    def set_headers(self, headers):
        for name in headers:
            self.set_header(name, headers[name])

    def send_response(self, status_code=200, data=None, headers=None):
        """ Set REST API response """
        self.set_status(status_code, None)
        if headers is not None:
            self.set_headers(headers)
        if data:
            data = json.dumps(data, default=json_default)
        else:
            data = ""

        self.finish(data)

    def finish(self, chunk=None):
        super(APIBaseHandler, self).finish(chunk)
        self._time_end = time.time()

    def add_to_log(self, action, info=None, level="info"):
        log = {}
        log["action"] = strip_tags(action)
        log["info"] = strip_tags(info)
        log["level"] = strip_tags(level)
        log["created"] = int(time.time())
        self.db.logs.insert(log)

    def json_decode(self, text):
        try:
            data = json.loads(text)
        except:
            data = json.loads(urllib.unquote_plus(text))

        return data


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

@route(r"/api/v2/users")
class UsersHandler(APIBaseHandler):
    """Handle users
    - Take application ID and secret
    - Create user
    """

    def post(self):
        """Register user
        """
        username = self.get_argument("username")
        password = self.get_argument("password")
        email = self.get_argument("email")
        now = int(time.time())
        user = {
            "username": username,
            "password": password,
            "email": email,
            "created": now,
        }
        try:
            cursor = self.db.users.find_one({"username": username})
            if cursor:
                self.send_response(BAD_REQUEST, dict(error="Username already exists"))
            else:
                userid = self.db.users.insert(user)
                self.add_to_log("Add user", username)
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
                data = self.json_decode(where)
            except Exception as ex:
                self.send_response(BAD_REQUEST, dict(error=str(ex)))

        cursor = self.db.users.find(data)
        users = []
        for u in cursor:
            users.append(u)
        self.send_response(OK, users)
