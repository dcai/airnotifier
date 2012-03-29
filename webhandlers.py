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
from apns import *
import re
from hashlib import sha1
from tornado.options import define, options

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
        return self.application.db

    @property
    def apnsconnections(self):
        """ APNs connections"""
        return self.application.apnsconnections

    def get_current_user(self):
        """ Get current user from cookie """

        user_json = self.get_secure_cookie('user')
        if not user_json:
            return None
        return tornado.escape.json_decode(user_json)

class MainHandler(WebBaseHandler):
    """ Redirect to default view """
    def get(self):
        self.redirect(r"/applications/")


class AuthHandler(WebBaseHandler, tornado.auth.GoogleMixin):
    """ Google authentication """
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument('openid.mode', None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()

    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, 'Google auth failed')
        self.set_secure_cookie('user', tornado.escape.json_encode(user))
        self.redirect(r"/applications/")


class LogoutHandler(WebBaseHandler):
    """ Logout and clearn cookies """
    def get(self):
        self.clear_cookie('user')
        self.redirect(r"/")

class AppActionHandler(WebBaseHandler):
    def get(self, appname, action):
        app = self.db.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)
        if action == 'delete':
            self.render("app_delete.html", app=app)
        elif action == 'tokens':
            tokens = self.db.tokens.find({'appname': appname})
            logging.info(tokens)
            self.render("app_tokens.html", app=app, tokens=tokens)
        elif action == 'keys':
            keys = self.db.keys.find({'appname': appname})
            self.render("app_keys.html", app=app, keys=keys)
            pass
        elif action == 'broadcast':
            self.render("app_broadcast.html", app=app)
            pass
        elif action == 'objects':
            pass

    def post(self, appname, action):
        app = self.db.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)
        if action == 'delete':
            self.db.applications.remove({'shortname': appname})
        self.redirect(r"/applications/")

class AppHandler(WebBaseHandler):
    def get(self, appname):
        if appname == "new":
            self.render("newapp.html")
        else:
            #app = self.db.get("select * from applications where shortname = %s", appname)
            app = self.db.applications.find_one({'shortname': appname})
            if not app: raise tornado.web.HTTPError(500)
            self.render("app.html", app=app)

    def make_appname(self, appname):
        return re.sub(r'\W+', '', appname)

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
                #apn = APNClient(options.apns, app['certfile'], app['keyfile'], app['shortname'], instanceid)
                #self.apnsconnections[app['shortname']].append(apn)

    def post(self, appname):
        update = True
        if appname == 'new':
            # Create a new app
            update = False
            app = {}
            appname = self.make_appname(self.get_argument('appshortname').strip().lower())
            app['shortname'] = appname
        else:
            appname = self.make_appname(appname)
            app = self.db.applications.find_one({'shortname':appname})

        # Update app details
        if self.request.files:
            if self.request.files['appcertfile'][0]:
                certfile = self.request.files['appcertfile'][0]
                certfilename = sha1(certfile['body']).hexdigest()
                certfilepath = options.pemdir + certfilename
                thefile = open(certfilepath, "w")
                thefile.write(certfile['body'])
                thefile.close()
                app['certfile'] = certfilepath

            if self.request.files['appkeyfile'][0]:
                keyfile = self.request.files['appkeyfile'][0]
                keyfilename = sha1(keyfile['body']).hexdigest()
                keyfilepath = options.pemdir + keyfilename
                thefile = open(keyfilepath, "w")
                thefile.write(keyfile['body'])
                thefile.close()
                app['keyfile'] = keyfilepath

        if self.get_argument('appdescription'):
            app['description'] = self.get_argument('appdescription')

        if self.get_argument('connections'):
            """If this value is greater than current apns connections,
            creating more
            If less than current apns connections, kill extra instances
            """
            app['connections'] = int(self.get_argument('connections'))

        if self.get_argument('appfullname'):
            app['fullname'] = self.get_argument('appfullname')

        enableapns = self.get_argument('enableapns', None)
        if not enableapns:
            """TODO Kill all APNs connections"""
            app['enableapns'] = 0
        else:
            """TODO Start APNs connections if none"""
            app['enableapns'] = 1
            self.start_apns(app)

        #updatedfields = buildUpdateFields(fields)
        #sql = "UPDATE applications SET %s WHERE shortname = \"%s\"" % (updatedfields, appname)
        #logging.info(sql)
        #apps = self.db.execute(sql)
        if update:
            self.db.applications.update({'shortname': appname}, app)
        else:
            self.db.applications.insert(app)
        self.redirect(r"/applications/%s" % appname)

class AppsListHandler(WebBaseHandler):

    #@tornado.web.authenticated
    def get(self):
        #fullname = tornado.escape.xhtml_escape(self.current_user['name'])
        #apps = self.db.query("SELECT * FROM applications ORDER BY timemodified")
        apps = self.db.applications.find()
        self.render('apps.html', apps=apps)

class StatsHandler(WebBaseHandler):
    def get(self):
        #records = self.db.query("SELECT * FROM applications ORDER BY timemodified")
        records = self.db.applications.find()
        apps = {};
        for app in records:
            logging.info(app)
            shortname = app['shortname']
            apps[shortname] = app
        self.render('stats.html', apps=apps, apns=self.apnsconnections)
