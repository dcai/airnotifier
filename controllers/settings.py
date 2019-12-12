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
from constants import (
    DEVICE_TYPE_IOS,
    VERSION,
    KEY_APNS_AUTHKEY,
    KEY_APNS_BUNDLEID,
    KEY_APNS_KEYID,
    KEY_APNS_TEAMID,
    KEY_FCM_PROJECT_ID,
    KEY_FCM_JSON_KEY,
)

from pymongo import DESCENDING
from util import *
import sys
from api import API_PERMISSIONS
from pushservices.wns import WNSClient
from pushservices.fcm import FCMClient
from pushservices.apns import ApnsClient
import requests
import traceback
from controllers.base import *


@route(r"/applications/([^/]+)/settings[\/]?")
class AppHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        if appname == "new":
            self.redirect(r"/create/app")
        else:
            app = self.dao.find_app_by_name(appname)
            if not app:
                self.finish("Application doesn't exist")
                # self.redirect(r"/applications/new")
                # raise tornado.web.HTTPError(500)
            else:
                self.render("app_settings.html", app=app)

    @tornado.web.authenticated
    def post(self, appname):
        try:
            self.appname = appname
            app = self.dao.find_app_by_name(appname)

            if self.get_argument("appfullname", None):
                app["fullname"] = self.get_argument("appfullname")

            if self.get_argument("appdescription", None):
                app["description"] = self.get_argument("appdescription")

            if self.get_argument("blockediplist", None):
                app["blockediplist"] = self.get_argument("blockediplist").strip()
            else:
                app["blockediplist"] = ""

            self.update_fcm_settings(app)
            self.update_apns_settings(app)

            updatewnsaccesstoken = False
            if self.get_argument("wnsclientid", None):
                wnsclientid = self.get_argument("wnsclientid").strip()
                if not wnsclientid == app.get("wnsclientid", ""):
                    app["wnsclientid"] = wnsclientid
                    updatewnsaccesstoken = True

            if self.get_argument("wnsclientsecret", None):
                wnsclientsecret = self.get_argument("wnsclientsecret").strip()
                if not wnsclientsecret == app.get("wnsclientsecret", ""):
                    app["wnsclientsecret"] = wnsclientsecret
                    updatewnsaccesstoken = True

            if updatewnsaccesstoken:
                url = "https://login.live.com/accesstoken.srf"
                payload = {
                    "grant_type": "client_credentials",
                    "client_id": app["wnsclientid"],
                    "client_secret": app["wnsclientsecret"],
                    "scope": "notify.windows.com",
                }
                response = requests.post(url, data=payload)
                responsedata = response.json()
                if response.status_code != 200:
                    raise Exception("Invalid WNS secret")
                if "access_token" in responsedata and "token_type" in responsedata:
                    app["wnsaccesstoken"] = responsedata["access_token"]
                    app["wnstokentype"] = responsedata["token_type"]
                    app["wnstokenexpiry"] = int(responsedata["expires_in"]) + int(
                        time.time()
                    )
                    ## Update connections too
                    self.wnsconnections[app["shortname"]] = []
                    wns = WNSClient(self.masterdb, app, 0)
                    self.wnsconnections[app["shortname"]].append(wns)

            self.dao.update_app_by_name(self.appname, app)
            self.redirect(r"/applications/%s/settings" % self.appname)
        except Exception as ex:
            logging.error(traceback.format_exc())
            self.render("app_settings.html", app=app, error=str(ex))

    def update_apns_settings(self, app):
        should_update = False

        team_id = self.get_argument(KEY_APNS_TEAMID, None)
        if team_id:
            if app.get(KEY_APNS_TEAMID, "") != team_id.strip():
                app[KEY_APNS_TEAMID] = team_id.strip()
                should_update = True

        bundle_id = self.get_argument(KEY_APNS_BUNDLEID, None)
        if bundle_id:
            if app.get(KEY_APNS_BUNDLEID, "") != bundle_id.strip():
                app[KEY_APNS_BUNDLEID] = bundle_id.strip()
                should_update = True

        key_id = self.get_argument(KEY_APNS_KEYID, None)
        if key_id:
            if app.get(KEY_APNS_KEYID, "") != key_id.strip():
                app[KEY_APNS_KEYID] = key_id.strip()
                should_update = True

        auth_key = self.get_argument(KEY_APNS_AUTHKEY, None)
        if auth_key:
            if app.get(KEY_APNS_AUTHKEY, "") != auth_key.strip():
                app[KEY_APNS_AUTHKEY] = auth_key.strip()
                should_update = True

        if should_update:
            apns = ApnsClient(
                auth_key=app[KEY_APNS_AUTHKEY],
                bundle_id=app[KEY_APNS_BUNDLEID],
                key_id=app[KEY_APNS_KEYID],
                team_id=app[KEY_APNS_TEAMID],
                appname=app["shortname"],
                instanceid=0,
            )
            self.apnsconnections[app["shortname"]] = [apns]

    def update_fcm_settings(self, app):
        update_fcm = False
        if self.get_argument(KEY_FCM_PROJECT_ID, None):
            if (
                app.get(KEY_FCM_PROJECT_ID, "")
                != self.get_argument(KEY_FCM_PROJECT_ID).strip()
            ):
                app[KEY_FCM_PROJECT_ID] = self.get_argument(KEY_FCM_PROJECT_ID).strip()
                update_fcm = True

        if self.get_argument(KEY_FCM_JSON_KEY, None):
            if (
                app.get(KEY_FCM_JSON_KEY, "")
                != self.get_argument(KEY_FCM_JSON_KEY).strip()
            ):
                app[KEY_FCM_JSON_KEY] = self.get_argument(KEY_FCM_JSON_KEY).strip()
                update_fcm = True

        if update_fcm:
            # reset fcm connections
            try:
                fcm = FCMClient(
                    project_id=app[KEY_FCM_PROJECT_ID],
                    jsonkey=app[KEY_FCM_JSON_KEY],
                    appname=app["shortname"],
                    instanceid=0,
                )
                self.fcmconnections[app["shortname"]] = [fcm]
            except Exception as ex:
                logging.info(ex)
