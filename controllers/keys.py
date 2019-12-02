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
import sys, os
import tornado.web
from api import API_PERMISSIONS
from controllers.base import *
from util import *
import logging


@route(r"/applications/([^/]+)/keys")
class AppAccessKeysHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({"shortname": appname})
        if not app:
            raise tornado.web.HTTPError(500)
        keys = self.db.keys.find()
        key_to_be_deleted = self.get_argument("delete", None)
        key_to_be_edited = self.get_argument("edit", None)
        if key_to_be_edited:
            key = self.db.keys.find_one({"key": key_to_be_edited})
            self.render(
                "app_edit_key.html",
                app=app,
                keys=keys,
                key=key,
                map=list(API_PERMISSIONS.items()),
            )
            return
        if key_to_be_deleted:
            self.db.keys.remove({"key": key_to_be_deleted})
            self.redirect("/applications/%s/keys" % appname)
        self.render(
            "app_keys.html",
            app=app,
            keys=keys,
            newkey=None,
            map=list(API_PERMISSIONS.items()),
        )

    @tornado.web.authenticated
    def post(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({"shortname": appname})
        if not app:
            raise tornado.web.HTTPError(500)
        key = {}
        key["contact"] = self.get_argument("keycontact").strip()
        action = self.get_argument("action").strip()
        key["description"] = self.get_argument("keydesc").strip()
        key["created"] = int(time.time())
        permissions = self.get_arguments("permissions[]")
        result = 0
        for permission in permissions:
            result = result | int(permission)
        key["permission"] = result
        # make key as shorter as possbile
        if action == "create":
            key["key"] = create_access_key()
            # Alternative key generator, this is SHORT
            # crc = binascii.crc32(str(uuid.uuid4())) & 0xffffffff
            # key['key'] = '%08x' % crc
            keyObjectId = self.db.keys.insert(key)
            self.redirect("/applications/%s/keys" % appname)
        else:
            key["key"] = self.get_argument("accesskey").strip()
            self.db.keys.update({"key": key["key"]}, key)
            self.redirect("/applications/%s/keys" % appname)
