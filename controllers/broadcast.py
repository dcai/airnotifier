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


@route(r"/applications/([^/]+)/broadcast")
class AppBroadcastHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({"shortname": appname})
        if not app:
            raise tornado.web.HTTPError(500)
        self.render("app_broadcast.html", app=app, sent=False)

    @tornado.web.authenticated
    def post(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({"shortname": appname})
        if not app:
            raise tornado.web.HTTPError(500)
        alert = self.get_argument("notification").strip()
        sound = "default"
        channel = "default"
        self.application.send_broadcast(
            self.appname, self.db, channel=channel, alert=alert, sound=sound
        )
        self.render("app_broadcast.html", app=app, sent=True)


@route(r"/applications/([^/]+)/broadcast/status")
class AppBroadcastStatusHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        self.write(self.application.get_broadcast_status(appname))
