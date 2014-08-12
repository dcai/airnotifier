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
import logging

@route(r"/create/app")
class AppCreateNewHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("app_new.html")
    @tornado.web.authenticated
    def post(self):
        # Create a new app
        app = {}
        self.appname = filter_alphabetanum(self.get_argument('appshortname').strip().lower())
        app['shortname'] = self.appname
        app['environment'] = 'sandbox'
        app['enableapns'] = 0
        app['connections'] = 1
        app['blockediplist'] = ''
        app['gcmprojectnumber'] = ''
        app['gcmapikey'] = ''
        if self.get_argument('appfullname', None):
            app['fullname'] = self.get_argument('appfullname')
        else:
            app['fullname'] = self.appname

        if self.get_argument('appdescription', None):
            app['description'] = self.get_argument('appdescription')
        else:
            app['description'] = ""

        current_app = self.masterdb.applications.find_one({'shortname': self.appname})
        if not current_app:
            self.masterdb.applications.insert(app)
        self.redirect(r"/applications/%s/settings" % self.appname)
