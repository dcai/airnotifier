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

import tornado.web
from controllers.base import *
from util import filter_alphabetanum

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


@route(r"/create/app")
class AppCreateNewHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("app_new.html", currentuser=self.currentuser)

    @tornado.web.authenticated
    def post(self):
        # Create a new app
        app = {}
        self.appname = filter_alphabetanum(
            self.get_argument("appshortname").strip().lower()
        )
        app["shortname"] = self.appname
        if self.currentuser["orgid"] == 0:
            app["orgid"] = int(self.get_argument("orgid", 0))
        else:
            app["orgid"] = self.currentuser["orgid"]
        app["blockediplist"] = ""
        app["clickatellusername"] = ""
        app["clickatellpassport"] = ""
        app["clickatellappid"] = ""
        app[KEY_APNS_AUTHKEY] = ""
        app[KEY_APNS_BUNDLEID] = ""
        app[KEY_APNS_KEYID] = ""
        app[KEY_APNS_TEAMID] = ""
        app[KEY_FCM_JSON_KEY] = ""
        app[KEY_FCM_PROJECT_ID] = ""
        if self.get_argument("appfullname", None):
            app["fullname"] = self.get_argument("appfullname")
        else:
            app["fullname"] = self.appname

        if self.get_argument("appdescription", None):
            app["description"] = self.get_argument("appdescription")
        else:
            app["description"] = ""

        current_app = self.masterdb.applications.find_one({"shortname": self.appname})
        if not current_app:
            self.masterdb.applications.insert(app)
            indexes = [("created", DESCENDING)]
            self.db["tokens"].create_index(indexes)
            self.db["logs"].create_index(indexes)
        self.redirect(r"/applications/%s/settings" % self.appname)
