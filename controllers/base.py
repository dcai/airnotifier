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

from routes import route
import platform
import tornado.web
import time
from constants import DEVICE_TYPE_IOS, VERSION
from pymongo import DESCENDING
from util import *
from tornado.options import options
from dao import Dao
import sys


def buildUpdateFields(params):
    """Join fields and values for SQL update statement
    """
    return ",".join(['%s = "%s"' % (k, v) for k, v in list(params.items())])


def normalize_tokens(tokens):
    for token in tokens:
        if not "device" in token:
            token["device"] = DEVICE_TYPE_IOS
    return tokens


class WebBaseHandler(tornado.web.RequestHandler):
    """WebBaseHandler class to precess Web traffic
    """

    def initialize(self):
        self.dao = self.application.container.dao

    def prepare(self):
        pass

    @property
    def dbname(self):
        """ DB name"""
        return options.appprefix + self.appname

    @property
    def db(self):
        """ DB instance """
        return self.application.mongodb[self.dbname]

    @property
    def mongodbconnection(self):
        """ mongodb connection """
        return self.application.mongodb

    @property
    def masterdb(self):
        return self.application.masterdb

    @property
    def apnsconnections(self):
        """ APNs connections """
        return self.application.services["apns"]

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
    def currentuser(self):
        return self.get_current_user()

    def get_current_user(self):
        """ Get current user from cookie """

        userid = self.get_secure_cookie("user")
        if not userid:
            return None
        userId = ObjectId(userid.decode("utf-8"))
        user = self.masterdb.managers.find_one({"_id": userId})
        return user

    def render_string(self, template_name, **kwargs):
        apps = []
        if self.currentuser and "orgid" in self.currentuser:
            currentuser_orgid = self.currentuser["orgid"]
            if currentuser_orgid == 0:
                apps = self.masterdb.applications.find()
            else:
                apps = self.masterdb.applications.find({"orgid": currentuser_orgid})
        kwargs["apps"] = apps
        return super(WebBaseHandler, self).render_string(template_name, **kwargs)


@route(r"/")
class MainHandler(WebBaseHandler):
    """ Redirect to default view """

    @tornado.web.authenticated
    def get(self):
        self.redirect(r"/applications")


@route(r"/applications/([^/]+)/delete")
class AppDeletionHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({"shortname": appname})
        if not app:
            raise tornado.web.HTTPError(500)
        self.render("app_delete.html", app=app)

    @tornado.web.authenticated
    def post(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({"shortname": appname})
        if not app:
            raise tornado.web.HTTPError(500)
        self.masterdb.applications.remove({"shortname": appname})
        self.mongodbconnection.drop_database(appname)
        self.redirect(r"/applications")


@route(r"/applications/([^/]+)/logs")
class AppLogViewHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({"shortname": appname})
        if not app:
            raise tornado.web.HTTPError(500)
        page = self.get_argument("page", None)
        perpage = 50
        if page:
            logs = (
                self.db.logs.find()
                .sort("created", DESCENDING)
                .skip(int(page) * perpage)
                .limit(perpage)
            )
        else:
            page = 0
            logs = self.db.logs.find().sort("created", DESCENDING).limit(perpage)
        self.render("app_logs.html", app=app, logs=logs, page=int(page))

    def post(self, appname):
        self.appname = appname
        now = int(time.time())
        thirtydaysago = now - 60 * 60 * 24 * 30
        self.db.logs.remove({"created": {"$lt": thirtydaysago}})
        self.redirect(r"/applications/%s/logs" % appname)


@route(r"/applications/([^/]+)/objects")
class AppObjectsHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, appname):
        self.appname = appname
        app = self.masterdb.applications.find_one({"shortname": appname})
        if not app:
            raise tornado.web.HTTPError(500)
        objects = self.db.objects.find()
        self.render("app_objects.html", app=app, objects=objects)


@route(r"/applications/([^/]+)")
class AppHandler(WebBaseHandler):  # @DuplicatedSignature
    """
    Just redirection
    """

    @tornado.web.authenticated
    def get(self, appname):
        self.redirect(r"/applications/%s/settings" % appname)


@route(r"/applications")
class AppsListHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self):
        version_object = self.masterdb["options"].find_one({"name": "version"})
        outdated = False
        if int(version_object["value"]) < int(VERSION):
            outdated = True
        apps = self.masterdb.applications.find()
        self.render("apps.html", apps=apps, outdated=outdated)


@route(r"/stats/")
class StatsHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self):
        records = self.masterdb.applications.find()
        self.render("stats.html", apns=self.apnsconnections)


@route(r"/info/")
class InfoHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self):
        airnotifierinfo = {}
        airnotifierinfo["version"] = VERSION
        mongodbinfo = self.application.mongodb.server_info()
        if "versionArray" in mongodbinfo:
            del mongodbinfo["versionArray"]
        pythoninfo = {}
        pythoninfo["version"] = sys.version
        pythoninfo["platform"] = sys.platform
        pythoninfo["os"] = os.name
        pythoninfo["arch"] = platform.architecture()
        pythoninfo["machine"] = platform.machine()
        pythoninfo["build"] = platform.python_build()[1]
        pythoninfo["compiler"] = platform.python_compiler()
        pythoninfo["modules"] = ", ".join(sys.builtin_module_names)

        self.render(
            "info.html",
            airnotifierinfo=airnotifierinfo,
            pythoninfo=pythoninfo,
            mongodb=mongodbinfo,
            tornadoversion=tornado.version,
        )


@route(r"/admin/([^/]+)")
class AdminHandler(WebBaseHandler):
    @tornado.web.authenticated
    def get(self, action):
        if self.get_argument("delete", None):
            user_id = self.get_argument("delete", None)
            if user_id:
                self.masterdb.managers.remove({"_id": ObjectId(user_id)})
                self.redirect("/admin/managers")
                return
        currentuser_orgid = self.currentuser["orgid"]
        if currentuser_orgid == 0:
            managers = self.masterdb.managers.find()
        else:
            managers = self.masterdb.managers.find({"orgid": currentuser_orgid})

        self.render(
            "managers.html",
            managers=managers,
            created=None,
            updated=None,
            currentuser=self.currentuser,
        )

    def post(self, action):
        action = self.get_argument("action", "")
        if action == "createuser":
            user = {}
            user["created"] = int(time.time())
            user["email"] = self.get_argument("newemail").strip()
            password = self.get_argument("newpassword").strip()
            passwordhash = get_password(password, options.passwordsalt)
            user["password"] = passwordhash
            user["level"] = "manager"
            currentuser_orgid = self.currentuser["orgid"]
            if currentuser_orgid == 0:
                user["orgid"] = int(self.get_argument("orgid", 0))
            else:
                user["orgid"] = currentuser_orgid
            result = self.masterdb.managers.update(
                {"email": user["email"]}, user, upsert=True
            )
            managers = self.masterdb.managers.find()
            if result["updatedExisting"]:
                self.render(
                    "managers.html",
                    managers=managers,
                    updated=user,
                    created=None,
                    currentuser=self.currentuser,
                )
            else:
                self.render(
                    "managers.html",
                    managers=managers,
                    updated=None,
                    created=user,
                    currentuser=self.currentuser,
                )
        elif action == "changepassword":
            password = self.get_argument("newpassword").strip()
            passwordhash = get_password(password, options.passwordsalt)
            self.masterdb.managers.update(
                {"email": self.currentuser["email"]},
                {"$set": {"password": passwordhash}},
            )
            managers = self.masterdb.managers.find()
            user = self.currentuser
            self.render(
                "managers.html",
                managers=managers,
                updated=user,
                created=None,
                currentuser=self.currentuser,
            )
