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
import json
import oauth
import test
import random
from hashlib import sha1
## Tornado modules
import tornado.auth
import tornado.httpserver
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.database
import tornado.web
from tornado.options import define, options
## APNs library
from apns import *
## Handlers
from apihandlers import *
from webhandlers import *
## UI modules
from uimodules import AppBlockModule

define("certfile", default="cert.pem", help="Certificate file")
define("keyfile", default="key.pem", help="Private key file")
define("disableapns", default=False, help="Not using APNs")
define("apns", default=(), help="APNs")
define("pemdir", default="pemdir", help="")
define("passwordsalt", default="d2o0n1g2s0h3e1n1g", help="Being used to make password hash")

define("dbtype", default="mysql", help="Database type")
define("dbhost", default="localhost", help="Database host")
define("dbname", default="airnotifier", help="Database name")
define("dbuser", default="af", help="Database user")
define("dbpassword", default="", help="Database user password")


#logging.getLogger().setLevel(logging.DEBUG)

class AirNotifierApp(tornado.web.Application):

    def __init__(self, apnsconnections={}):
        app_settings = dict(
            debug=True,
            app_title=u'AirNotifier',
            ui_modules={"AppBlock": AppBlockModule},
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
                    (r"/tokens/([^/]+)", TokenHandler),
                    (r"/users/", UserHandler),
                    (r"/objects/", ObjectHandler),
                    ## Web
                    (r"/applications/", AppsListHandler),
                    (r"/applications/([^/]+)", AppHandler),
                    (r"/applications/([^/]+)/([^/]+)", AppActionHandler),
                    (r"/stats/", StatsHandler),
                    # authentication session
                    (r"/auth/login", AuthHandler),
                    (r"/auth/logout", LogoutHandler),
                    ]

        tornado.web.Application.__init__(self, handlers, **app_settings)

        self.db = tornado.database.Connection(
                host=options.dbhost, database=options.dbname,
                user=options.dbuser, password=options.dbpassword)

if __name__ == "__main__":
    tornado.options.parse_config_file("airnotifier.conf")
    tornado.options.parse_command_line()
    db = tornado.database.Connection(
            host=options.dbhost, database=options.dbname,
            user=options.dbuser, password=options.dbpassword)

    sql = "SELECT a.id, a.shortname, a.certfile, a.keyfile, a.connections FROM applications a WHERE a.enableapns=1"
    apps = db.query(sql)

    apnsconns = {}
    for app in apps:
        logging.info(app)
        apnsconns[app.shortname] = []
        if int(app.connections) > 5:
            app.connections = 5
        if int(app.connections) < 1:
            app.connections = 1
        for instanceid in range(0, app.connections):
            apn = APNClient(options.apns, app.certfile, app.keyfile, app.shortname, instanceid)
            apnsconns[app.shortname].append(apn)

    # Job done, closing
    db.close()

    logging.info("Starting AirNotifier server")
    http_server = tornado.httpserver.HTTPServer(AirNotifierApp(apnsconnections=apnsconns))
    http_server.listen(8000)
    tornado.ioloop.IOLoop.instance().start()
