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
import logging
import random
import unicodedata
from apns import *
import re
from hashlib import sha1
from tornado.options import define, options
from pymongo import *
from bson import *

def buildUpdateFields(params):
    """Join fields and values for SQL update statement
    """
    return ",".join(["%s = \"%s\"" % (k, v) for k, v in params.items()])

class WebBaseHandler(tornado.web.RequestHandler):
    """WebBaseHandler class to precess Web traffic
    """
    def initialize(self):
        pass

    def prepare(self):
        pass

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

    def get_current_user(self):
        """ Get current user from cookie """

        userid = self.get_secure_cookie('user')
        if not userid:
            return None
        userId = ObjectId(userid)
        user = self.masterdb.managers.find_one({'_id': userId})
        return user

class AuthHandler(WebBaseHandler):
    def get(self, action):
        next = self.get_argument('next', "/")
        if action == 'logout':
            self.clear_cookie('user')
            self.redirect(next)
        else:
            self.render('login.html')

    def post(self, action):
        next = self.get_argument('next', "/")
        if action == 'logout':
            self.clear_cookie('user')
        else:
            username = self.get_argument('username', None)
            password = self.get_argument('password', None)
            passwordhash = sha1(password).hexdigest()
            user = self.masterdb.managers.find_one({'username': username, 'password': passwordhash})
            if user:
                self.set_secure_cookie('user', str(user['_id']))
        self.redirect(next)


class MainHandler(WebBaseHandler):
    """ Redirect to default view """
    @tornado.web.authenticated
    def get(self):
        self.redirect(r"/applications")

class AppActionHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname, action):
        self.appname = appname
        app = self.masterdb.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)
        if action == 'delete':
            self.render("app_delete.html", app=app)
        elif action == 'tokens':
            tokens = self.db.tokens.find()
            self.render("app_tokens.html", app=app, tokens=tokens)
        elif action == 'keys':
            keys = self.db.keys.find()
            self.render("app_keys.html", app=app, keys=keys, newkey=None)
        elif action == 'broadcast':
            self.render("app_broadcast.html", app=app, sent=False)
        elif action == 'objects':
            objects = self.db.objects.find()
            self.render("app_objects.html", app=app, objects=objects)
        elif action == 'logs':
            logs = self.db.logs.find()
            self.render("app_logs.html", app=app, logs=logs)

    @tornado.web.authenticated
    def post(self, appname, action):
        self.appname = appname
        app = self.masterdb.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)
        if action == 'delete':
            self.masterdb.applications.remove({'shortname': appname})
            self.redirect(r"/applications")
        elif action == 'keys':
            import uuid
            key = {}
            key['created'] = int(time.time())
            key['owner'] = self.get_argument('keyowner').strip()
            key['contact'] = self.get_argument('keyownercontact').strip()
            key['key'] = str(uuid.uuid4())
            keyObjectId = self.db.keys.insert(key)
            keys = self.db.keys.find()
            self.render("app_keys.html", app=app, keys=keys, newkey=key)
        elif action == 'broadcast':
            alert = self.get_argument('notification').strip()
            sound = 'default'
            badge = 1
            pl = PayLoad(alert=alert, sound=sound, badge=1)
            count = len(self.apnsconnections[app['shortname']])
            random.seed(time.time())
            instanceid = random.randint(0, count-1)
            conn = self.apnsconnections[app['shortname']][instanceid]
            tokens = self.db.tokens.find()
            try:
                for token in tokens:
                    conn.send(token['token'], pl)
            except Exception, ex:
                logging.info(ex)
            self.render("app_broadcast.html", app=app, sent=True)

class AppHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        if appname == "new":
            self.render("app_new.html")
        else:
            #app = self.db.get("select * from applications where shortname = %s", appname)
            app = self.masterdb.applications.find_one({'shortname': appname})
            if not app: raise tornado.web.HTTPError(500)
            self.render("app_settings.html", app=app)

    def make_appname(self, appname):
        appname = unicodedata.normalize("NFKD", appname).encode("ascii", "ignore")
        appname = re.sub(r"[^\w]+", " ", appname)
        appname = "".join(appname.lower().strip().split())
        return appname

    def start_apns(self, app):
        if not self.apnsconnections.has_key(app['shortname']):
            self.apnsconnections[app['shortname']] = []
            count = app['connections']

            for instanceid in range(0, count):
                apn = APNClient(options.apns, app['certfile'], app['keyfile'], app['shortname'], instanceid)
                self.apnsconnections[app['shortname']].append(apn)
        else:
            return

    def stop_apns(self, app):
        if self.apnsconnections.has_key(app['shortname']):
            conns = self.apnsconnections[app['shortname']]
            for conn in conns:
                conn.disconnect()

    @tornado.web.authenticated
    def post(self, appname):
        update = True
        if appname == 'new':
            # Create a new app
            update = False
            app = {}
            self.appname = self.make_appname(self.get_argument('appshortname').strip().lower())
            app['shortname'] = appname
        else:
            self.appname = appname
            app = self.masterdb.applications.find_one({'shortname':self.appname})

        # Update app details
        if self.request.files:
            if self.request.files.has_key('appcertfile'):
                certfile = self.request.files['appcertfile'][0]
                certfilename = sha1(certfile['body']).hexdigest()
                logging.info(certfilename)
                certfilepath = options.pemdir + certfilename
                thefile = open(certfilepath, "w")
                thefile.write(certfile['body'])
                thefile.close()
                app['certfile'] = certfilepath

            if self.request.files.has_key('appkeyfile'):
                keyfile = self.request.files['appkeyfile'][0]
                keyfilename = sha1(keyfile['body']).hexdigest()
                logging.info(keyfilename)
                keyfilepath = options.pemdir + keyfilename
                thefile = open(keyfilepath, "w")
                thefile.write(keyfile['body'])
                thefile.close()
                app['keyfile'] = keyfilepath

        if self.get_argument('appdescription', None):
            app['description'] = self.get_argument('appdescription')

        if self.get_argument('connections', None):
            """If this value is greater than current apns connections,
            creating more
            If less than current apns connections, kill extra instances
            """
            app['connections'] = int(self.get_argument('connections'))

        if self.get_argument('appfullname', None):
            app['fullname'] = self.get_argument('appfullname')

        enableapns = self.get_argument('enableapns', None)
        if not enableapns:
            """TODO Kill all APNs connections"""
            app['enableapns'] = 0
        else:
            """TODO Start APNs connections if none"""
            app['enableapns'] = 1
            self.start_apns(app)

        if self.get_argument('launchapns', False):
            logging.info("start apns")
            app['enableapns'] = 1
            self.start_apns(app)

        if update:
            self.masterdb.applications.update({'shortname': self.appname}, app)
        else:
            self.masterdb.applications.insert(app)
        self.redirect(r"/applications/%s" % self.appname)

class AppsListHandler(WebBaseHandler):

    @tornado.web.authenticated
    def get(self):
        apps = self.masterdb.applications.find()
        self.render('apps.html', apps=apps)

class StatsHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self):
        records = self.masterdb.applications.find()
        apps = {};
        for app in records:
            shortname = app['shortname']
            apps[shortname] = app
        self.render('stats.html', apps=apps, apns=self.apnsconnections)

class InfoHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self):
        import sys
        import platform
        import os
        mongodbinfo = self.application.mongodb.server_info()
        del mongodbinfo['versionArray']
        pythoninfo = {}
        pythoninfo['version'] = sys.version
        pythoninfo['platform'] = sys.platform
        pythoninfo['os'] = os.name
        pythoninfo['arch'] = platform.architecture()
        pythoninfo['machine'] = platform.machine()
        pythoninfo['build'] = platform.python_build()[1]
        pythoninfo['compiler'] = platform.python_compiler()
        pythoninfo['modules'] = ", ".join(sys.builtin_module_names)

        self.render('info.html', pythoninfo=pythoninfo, mongodb=mongodbinfo, tornadoversion=tornado.version)
