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

# system
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
from apns import APNClient, APNFeedback, PayLoad
import sys
from controllers.api_controller import API_PERMISSIONS

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
    def mongodbconnection(self):
        """ mongodb connection """
        return self.application.mongodb

    @property
    def masterdb(self):
        return self.application.masterdb

    @property
    def apnsconnections(self):
        """ APNs connections"""
        return self.application.apnsconnections

    @property
    def currentuser(self):
        return self.get_current_user()

    def get_current_user(self):
        """ Get current user from cookie """

        userid = self.get_secure_cookie('user')
        if not userid:
            return None
        userId = ObjectId(userid)
        user = self.masterdb.managers.find_one({'_id': userId})
        return user

    def render_string(self, template_name, **kwargs):
        apps = self.masterdb.applications.find()
        kwargs["apps"] = apps
        return super(WebBaseHandler, self).render_string(template_name, **kwargs)

@route(r"/auth/([^/]+)")
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
            passwordhash = sha1("%s%s" % (options.passwordsalt, password)).hexdigest()
            user = self.masterdb.managers.find_one({'username': username, 'password': passwordhash})
            if user:
                self.set_secure_cookie('user', str(user['_id']))
        self.redirect(next)


@route(r"/")
class MainHandler(WebBaseHandler):
    """ Redirect to default view """
    @tornado.web.authenticated
    def get(self):
        self.redirect(r"/applications")

@route(r"/applications/([^/]+)/keys")
class AppAccessKeysHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)
        keys = self.db.keys.find()
        key_to_be_deleted = self.get_argument('delete', None)
        key_to_be_edited = self.get_argument('edit', None)
        if key_to_be_edited:
            key = self.db.keys.find_one({'key': key_to_be_edited})
            self.render("app_edit_key.html", app=app, keys=keys, key=key, map=API_PERMISSIONS.items())
            return
        if key_to_be_deleted:
            self.db.keys.remove({'key':key_to_be_deleted})
            self.redirect("/applications/%s/keys" % appname)
        self.render("app_keys.html", app=app, keys=keys, newkey=None, map=API_PERMISSIONS.items())
    @tornado.web.authenticated
    def post(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)
        key = {}
        key['contact'] = self.get_argument('keycontact').strip()
        action = self.get_argument('action').strip()
        key['description'] = self.get_argument('keydesc').strip()
        key['created'] = int(time.time())
        permissions = self.get_arguments('permissions[]')
        result = 0
        for permission in permissions:
            result = result | int(permission)
        key['permission'] = result
        # make key as shorter as possbile
        if action == 'create':
            key['key'] = md5(str(uuid.uuid4())).hexdigest()
            # Alternative key generator, this is SHORT
            # crc = binascii.crc32(str(uuid.uuid4())) & 0xffffffff
            # key['key'] = '%08x' % crc
            keyObjectId = self.db.keys.insert(key)
            self.redirect("/applications/%s/keys" % appname)
        else:
            key['key'] = self.get_argument('accesskey').strip()
            self.db.keys.update({'key': key['key']}, key, safe=True)
            self.redirect("/applications/%s/keys" % appname)

@route(r"/applications/([^/]+)/delete")
class AppDeletionHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)
        self.render("app_delete.html", app=app)
    @tornado.web.authenticated
    def post(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)
        self.masterdb.applications.remove({'shortname': appname}, safe=True)
        self.mongodbconnection.drop_database(appname)
        self.redirect(r"/applications")

def normalize_tokens(tokens):
    for token in tokens:
        if not 'device' in token:
            token['device'] = DEVICE_TYPE_IOS
    return tokens

@route(r"/applications/([^/]+)/tokens")
class AppTokensHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)
        page = self.get_argument('page', None)
        perpage = 50

        token_id = self.get_argument('delete', None)
        if token_id:
            self.db.tokens.remove({'_id':ObjectId(token_id)})
            self.redirect("/applications/%s/tokens" % appname)
            return
        if page:
            tokens = self.db.tokens.find().sort('created', DESCENDING).skip(int(page) * perpage).limit(perpage)
        else:
            page = 0
            tokens = self.db.tokens.find().sort('created', DESCENDING).limit(perpage)
        self.render("app_tokens.html", app=app, tokens=tokens, page=int(page))

    @tornado.web.authenticated
    def post(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)

@route(r"/applications/([^/]+)/broadcast")
class AppBroadcastHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)
        self.render("app_broadcast.html", app=app, sent=False)
    @tornado.web.authenticated
    def post(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)
        alert = self.get_argument('notification').strip()
        sound = 'default'
        pl = PayLoad(alert=alert, sound=sound)
        count = len(self.apnsconnections[app['shortname']])
        random.seed(time.time())
        instanceid = random.randint(0, count - 1)
        conn = self.apnsconnections[app['shortname']][instanceid]
        tokens = self.db.tokens.find()
        try:
            for token in tokens:
                conn.send(token['token'], pl)
        except Exception, ex:
            logging.info(ex)
        self.render("app_broadcast.html", app=app, sent=True)

@route(r"/applications/([^/]+)/logs")
class AppLogViewHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)
        page = self.get_argument('page', None)
        perpage = 50
        if page:
            logs = self.db.logs.find().sort('created', DESCENDING).skip(int(page) * perpage).limit(perpage)
        else:
            page = 0
            logs = self.db.logs.find().sort('created', DESCENDING).limit(perpage)
        self.render("app_logs.html", app=app, logs=logs, page=int(page))

@route(r"/applications/([^/]+)/objects")
class AppObjectsHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({'shortname':appname})
        if not app: raise tornado.web.HTTPError(500)
        objects = self.db.objects.find()
        self.render("app_objects.html", app=app, objects=objects)

@route(r"/applications/new")
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

        self.masterdb.applications.insert(app)
        self.redirect(r"/applications/%s/settings" % self.appname)

@route(r"/applications/([^/]+)/settings")
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
        if not self.apnsconnections.has_key(app['shortname']):
            self.apnsconnections[app['shortname']] = []
            count = app['connections']
            if not app.has_key('environment'):
                app['environment'] = 'sandbox'

            for instanceid in range(0, count):
                try:
                    apn = APNClient(app['environment'], app['certfile'], app['keyfile'], app['shortname'], instanceid)
                except Exception as ex:
                    logging.error(ex)
                    return
                self.apnsconnections[app['shortname']].append(apn)
        else:
            return

    def stop_apns(self, app):
        if self.apnsconnections.has_key(app['shortname']):
            conns = self.apnsconnections[app['shortname']]
            for conn in conns:
                conn.shutdown()
            del self.apnsconnections[app['shortname']]

    def perform_feedback(self, app):
        apn = APNFeedback(app['environment'], app['certfile'], app['keyfile'], app['shortname'])

    @tornado.web.authenticated
    def post(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({'shortname':self.appname})

        if self.get_argument('appfullname', None):
            app['fullname'] = self.get_argument('appfullname')
        else:
            app['fullname'] = self.appname

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


        if self.get_argument('blockediplist', None):
            app['blockediplist'] = self.get_argument('blockediplist').strip()
        else:
            app['blockediplist'] = ''

        if self.get_argument('gcmprojectnumber', None):
            app['gcmprojectnumber'] = self.get_argument('gcmprojectnumber').strip()

        if self.get_argument('gcmapikey', None):
            app['gcmapikey'] = self.get_argument('gcmapikey').strip()

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

        self.masterdb.applications.update({'shortname': self.appname}, app, safe=True)
        self.redirect(r"/applications/%s/settings" % self.appname)

@route(r"/applications/([^/]+)")
class AppHandler(WebBaseHandler): # @DuplicatedSignature
    '''
    Just redirection
    '''
    @tornado.web.authenticated
    def get(self, appname):
        self.redirect(r"/applications/%s/settings" % appname)

@route(r"/applications")
class AppsListHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self):
        apps = self.masterdb.applications.find()
        self.render('apps.html', apps=apps)

@route(r"/stats/")
class StatsHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self):
        records = self.masterdb.applications.find()
        self.render('stats.html', apns=self.apnsconnections)

@route(r"/info/")
class InfoHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self):
        airnotifierinfo = {}
        airnotifierinfo['version'] = VERSION
        mongodbinfo = self.application.mongodb.server_info()
        if mongodbinfo.has_key('versionArray'):
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

        self.render('info.html', airnotifierinfo=airnotifierinfo, pythoninfo=pythoninfo, mongodb=mongodbinfo, tornadoversion=tornado.version)

@route(r"/admin/([^/]+)")
class AdminHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, action):
        if self.get_argument('delete', None):
            user_id = self.get_argument('delete', None)
            if user_id:
                self.masterdb.managers.remove({'_id':ObjectId(user_id)})
                self.redirect("/admin/managers")
                return
        managers = self.masterdb.managers.find()
        self.render('managers.html', managers=managers, created=None, updated=None, currentuser=self.currentuser)

    def post(self, action):
        action = self.get_argument('action', "")
        if action == 'createuser':
            user = {}
            user['created'] = int(time.time())
            user['username'] = self.get_argument('newusername').strip()
            password = self.get_argument('newpassword').strip()
            passwordhash = sha1("%s%s" % (options.passwordsalt, password)).hexdigest()
            user['password'] = passwordhash
            user['level'] = "manager"
            result = self.masterdb.managers.update({'username': user['username']}, user, safe=True, upsert=True)
            managers = self.masterdb.managers.find()
            if result['updatedExisting']:
                self.render('managers.html', managers=managers, updated=user, created=None, currentuser=self.currentuser)
            else:
                self.render('managers.html', managers=managers, updated=None, created=user, currentuser=self.currentuser)
        elif action == 'changepassword':
            password = self.get_argument('newpassword').strip()
            passwordhash = sha1("%s%s" % (options.passwordsalt, password)).hexdigest()
            self.masterdb.managers.update({"username": self.currentuser['username']}, {"$set": {"password": passwordhash}})
            managers = self.masterdb.managers.find()
            user = self.currentuser
            self.render('managers.html', managers=managers, updated=user, created=None, currentuser=self.currentuser)

@route(r"/mu-4716c5c7-3cb80ee8-4515a4a4-35abf050")
class BlitzHandler(WebBaseHandler):
    def get(self):
        self.write('42')
