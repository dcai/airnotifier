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

## System modules
import logging
import sys
import json
import test
from pymongo import Connection
## Tornado modules
import tornado.auth
import tornado.httpserver
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.database
import tornado.web
from util import *
from tornado.options import define, options
## APNs library
from apns import *
## Handlers
from apihandlers import *
from webhandlers import *
## UI modules
from uimodules import *

define("port", default=8801, help="Application server listen port", type=int)

define("pemdir", default="pemdir", help="Directory to store pems")
define("passwordsalt", default="d2o0n1g2s0h3e1n1g", help="Being used to make password hash")

define("mongohost", default="localhost", help="MongoDB host name")
define("mongoport", default=27017, help="MongoDB port")

define("masterdb", default="airnotifier", help="MongoDB DB to store information")
define("dbprefix", default="obj_", help="Collection name prefix")


#logging.getLogger().setLevel(logging.DEBUG)

class AirNotifierApp(tornado.web.Application):

    def __init__(self, apnsconnections={}):
        app_settings = dict(
            debug=True,
            app_title=u'AirNotifier',
            ui_modules={"AppSideBar": AppSideBar, "NavBar": NavBar},
            template_path=os.path.join(os.path.dirname(__file__),
                    'templates'),
            static_path=os.path.join(os.path.dirname(__file__), 'static'
                    ),
            cookie_secret='airnotifiercookie',
            login_url=r"/auth/login",
            autoescape=None,
            )
        self.apnsconnections = apnsconnections
        handlers = [(r"/", MainHandler),
                    ## API
                    (r"/notification/", NotificationHandler),
                    (r"/broadcast/", BroadcastHandler),
                    (r"/tokens/([^/]+)", TokenHandler),
                    ## Create/Query users
                    (r"/users", UsersHandler),
                    ## Delete/Get/Update individual user
                    (r"/users/([^/]+)", UserHandler),
                    ## Create/Query objects
                    (r"/objects/([^/]+)", ClassHandler),
                    ## Delete/Get/Update individual object
                    (r"/objects/([^/]+)/([^/]+)", ObjectHandler),
                    ## Upload files
                    (r"/files", FilesHandler),
                    ## Web
                    (r"/applications", AppsListHandler),
                    (r"/applications/([^/]+)", AppHandler),
                    (r"/applications/([^/]+)/([^/]+)", AppActionHandler),
                    (r"/stats/", StatsHandler),
                    (r"/info/", InfoHandler),
                    (r"/admin/([^/]+)", AdminHandler),
                    # authentication session
                    (r"/auth/([^/]+)", AuthHandler),
                    # Blitz rush
                    (r"/mu-4716c5c7-3cb80ee8-4515a4a4-35abf050", BlitzHandler),
                    ]

        tornado.web.Application.__init__(self, handlers, **app_settings)

        try:
            mongodb = Connection(options.mongohost, options.mongoport)
        except ConnectionFailure, ex:
            error_log("Cannot not connect to MongoDB")
            sys.exit(1)
        self.mongodb = mongodb

        self.masterdb = mongodb[options.masterdb]
        assert self.masterdb.connection == self.mongodb

if __name__ == "__main__":
    tornado.options.parse_config_file("airnotifier.conf")
    tornado.options.parse_command_line()
    mongodb = Connection(options.mongohost, options.mongoport)
    masterdb = mongodb[options.masterdb]

    apps = masterdb.applications.find({'enableapns': 1})

    apnsconns = {}

    for app in apps:
        apnsconns[app['shortname']] = []
        conns = int(app['connections'])
        if conns > 5:
            conns = 5
        if conns < 1:
            conns = 1
        if not app.has_key('environment'):
            app['environment'] = 'sandbox'
        for instanceid in range(0, conns):
            apn = APNClient(app['environment'], app['certfile'], app['keyfile'], app['shortname'], instanceid)
            apnsconns[app['shortname']].append(apn)
    mongodb.close()

    logging.info("Starting AirNotifier server")
    http_server = tornado.httpserver.HTTPServer(AirNotifierApp(apnsconnections=apnsconns))
    http_server.listen(options.port)

    tornado.ioloop.IOLoop.instance().start()
