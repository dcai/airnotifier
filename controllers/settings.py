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

@route(r"/applications/([^/]+)/settings[\/]?")
class AppHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        if appname == "new":
            self.render("app_new.html")
        else:
            app = self.masterdb.applications.find_one({'shortname': appname})
            if not app:
                self.finish("Application doesn't exist")
                # self.redirect(r"/applications/new")
                # raise tornado.web.HTTPError(500)
            else:
                self.render("app_settings.html", app=app)

    def start_apns(self, app):
        self.apnsconnections[app['shortname']] = []
        count = app.get('connections', 1)
        if not 'environment' in app:
            app['environment'] = 'sandbox'

        for instanceid in range(0, count):
            apn = APNClient(app['environment'], app.get('certfile', ''), app.get('keyfile', ''), app['shortname'], instanceid)
            self.apnsconnections[app['shortname']].append(apn)

    def stop_apns(self, app):
        if app['shortname'] in self.apnsconnections:
            conns = self.apnsconnections[app['shortname']]
            for conn in conns:
                conn.shutdown()
            del self.apnsconnections[app['shortname']]

    def perform_feedback(self, app):
        apn = APNFeedback(app['environment'], app['certfile'], app['keyfile'], app['shortname'])

    def save_file(self, req):
        filename = sha1(req['body']).hexdigest()
        filepath = options.pemdir + filename
        thefile = open(filepath, "w")
        thefile.write(req['body'])
        thefile.close()
        return filename

    def rm_file(self, filename):
        fullpath = options.pemdir + filename
        if os.path.isfile(filename):
            os.remove(filename)
        elif os.path.isfile(fullpath):
            os.remove(fullpath)


    @tornado.web.authenticated
    def post(self, appname):
        try:
            self.appname = appname
            app = self.masterdb.applications.find_one({'shortname':self.appname})

            if self.get_argument('appfullname', None):
                app['fullname'] = self.get_argument('appfullname')
            else:
                app['fullname'] = self.appname

            # Update app details
            if self.request.files:
                if self.request.files.has_key('appcertfile'):
                    self.rm_file(app['certfile'])
                    app['certfile'] = self.save_file(self.request.files['appcertfile'][0])

                if self.request.files.has_key('appkeyfile'):
                    self.rm_file(app['keyfile'])
                    app['keyfile'] = self.save_file(self.request.files['appkeyfile'][0])

                if self.request.files.has_key('mpnscertificatefile'):
                    self.rm_file(app['mpnscertificatefile'])
                    app['mpnscertificatefile'] = self.save_file(self.request.files['mpnscertificatefile'][0])
                    ## Update connections
                    self.mpnsconnections[app['shortname']] = []
                    mpns = MPNSClient(self.masterdb, app, 0)
                    self.mpnsconnections[app['shortname']].append(mpns)

            if self.get_argument('appdescription', None):
                app['description'] = self.get_argument('appdescription')


            if self.get_argument('blockediplist', None):
                app['blockediplist'] = self.get_argument('blockediplist').strip()
            else:
                app['blockediplist'] = ''

            updategcm = False
            if self.get_argument('gcmprojectnumber', None):
                if app['gcmprojectnumber'] != self.get_argument('gcmprojectnumber').strip():
                    app['gcmprojectnumber'] = self.get_argument('gcmprojectnumber').strip()
                    updategcm = True

            if self.get_argument('gcmapikey', None):
                if app['gcmapikey'] != self.get_argument('gcmapikey').strip():
                    app['gcmapikey'] = self.get_argument('gcmapikey').strip()
                    updategcm = True

            if updategcm:
                ## Update connections too
                self.gcmconnections[app['shortname']] = []
                gcm = GCMClient(app['gcmprojectnumber'], app['gcmapikey'], app['shortname'], 0)
                self.gcmconnections[app['shortname']].append(gcm)

            if self.get_argument('connections', None):
                """If this value is greater than current apns connections,
                creating more
                If less than current apns connections, kill extra instances
                """
                if app['connections'] != int(self.get_argument('connections')):
                    app['connections'] = int(self.get_argument('connections'))
                    self.stop_apns(app)
                    self.start_apns(app)

            if self.get_argument('performfeedbacktask', None):
                self.perform_feedback(app)

            if self.get_argument('launchapns', None):
                logging.info("Start APNS")
                app['enableapns'] = 1
                self.start_apns(app)

            if self.get_argument('stopapns', None):
                logging.info("Shutdown APNS")
                app['enableapns'] = 0
                self.stop_apns(app)

            if self.get_argument('turnonproduction', None):
                app['environment'] = 'production'
                self.stop_apns(app)
                self.start_apns(app)

            if self.get_argument('turnonsandbox', None):
                app['environment'] = 'sandbox'
                self.stop_apns(app)
                self.start_apns(app)

            updatewnsaccesstoken = False
            if self.get_argument('wnsclientid', None):
                wnsclientid = self.get_argument('wnsclientid').strip()
                if not wnsclientid == app['wnsclientid']:
                    app['wnsclientid'] = wnsclientid
                    updatewnsaccesstoken = True

            if self.get_argument('wnsclientsecret', None):
                wnsclientsecret = self.get_argument('wnsclientsecret').strip()
                if not wnsclientsecret == app['wnsclientsecret']:
                    app['wnsclientsecret'] = wnsclientsecret
                    updatewnsaccesstoken = True

            if updatewnsaccesstoken:
                url = 'https://login.live.com/accesstoken.srf'
                payload = {'grant_type': 'client_credentials', 'client_id': app['wnsclientid'], 'client_secret': app['wnsclientsecret'], 'scope': 'notify.windows.com'}
                response = requests.post(url, data=payload)
                if response.status_code != 200:
                    raise Exception('Invalid WNS secret')
                if 'access_token' in responsedata and 'token_type' in responsedata:
                    app['wnsaccesstoken'] = responsedata['access_token']
                    app['wnstokentype'] = responsedata['token_type']
                    app['wnstokenexpiry'] = int(responsedata['expires_in']) + int(time.time())
                    ## Update connections too
                    self.wnsconnections[app['shortname']] = []
                    wns = WNSClient(self.masterdb, app, 0)
                    self.wnsconnections[app['shortname']].append(wns)

            self.masterdb.applications.update({'shortname': self.appname}, app, safe=True)
            self.redirect(r"/applications/%s/settings" % self.appname)
        except Exception, ex:
            self.render("app_settings.html", app=app, error=str(ex))
