#!/usr/bin/env python
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

import logging
import os
import time

from pymongo.connection import Connection
from tornado.options import define, options
import tornado.httpserver
import tornado.ioloop
import tornado.options

from apns import APNClient
from gcm.http import GCMClient
from uimodules import *
from util import error_log


define("port", default=8801, help="Application server listen port", type=int)

define("pemdir", default="pemdir", help="Directory to store pems")
define("passwordsalt", default="d2o0n1g2s0h3e1n1g", help="Being used to make password hash")
define("cookiesecret", default="airnotifiercookiesecret", help="Cookie secret")
define("debug", default=False, help="Debug mode")

define("mongohost", default="localhost", help="MongoDB host name")
define("mongoport", default=27017, help="MongoDB port")

define("masterdb", default="airnotifier", help="MongoDB DB to store information")
define("dbprefix", default="obj_", help="Collection name prefix")

logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')

class AirNotifierApp(tornado.web.Application):

    def init_routes(self):
        from routes import RouteLoader
        return RouteLoader.load('controllers')

    def __init__(self, apnsconnections={}, gcmconnections={}):
        tornado.options.parse_config_file("airnotifier.conf")
        tornado.options.parse_command_line()
        
        app_settings = dict(
            debug=True,
            # debug=options.debug,
            app_title=u'AirNotifier',
            ui_modules={"AppSideBar": AppSideBar, "NavBar": NavBar, "TabBar": TabBar},
            template_path=os.path.join(os.path.dirname(__file__), 'templates'),
            static_path=os.path.join(os.path.dirname(__file__), 'static'),
            cookie_secret=options.cookiesecret,
            login_url=r"/auth/login",
            autoescape=None,
            )
        self.apnsconnections = apnsconnections
        self.gcmconnections = gcmconnections

        handlers = self.init_routes()

        tornado.web.Application.__init__(self, handlers, **app_settings)

        mongodb = None
        while not mongodb:
            try:
                mongodb = Connection(options.mongohost, options.mongoport)
            except:
                error_log("Cannot not connect to MongoDB")
            time.sleep(5)

        self.mongodb = mongodb

        self.masterdb = mongodb[options.masterdb]
        assert self.masterdb.connection == self.mongodb
    def main(self):
        logging.info("Starting AirNotifier server")
        http_server = tornado.httpserver.HTTPServer(self)
        http_server.listen(options.port)
        logging.info("AirNotifier is running")
        tornado.ioloop.IOLoop.instance().start()

def init_messaging_agents():
    mongodb = None
    while not mongodb:
        try:
            mongodb = Connection(options.mongohost, options.mongoport)
        except Exception as ex:
            logging.error(ex)
        # wait 5 secs to reconnect
        time.sleep(5)
    masterdb = mongodb[options.masterdb]
    apps = masterdb.applications.find()
    httpconns = {}
    apnsconns = {}
    for app in apps:
        ''' APNs setup '''
        apnsconns[app['shortname']] = []
        conns = int(app['connections'])
        if conns < 1:
            conns = 1
        if 'environment' not in app:
            app['environment'] = 'sandbox'

        if 'certfile' in app and 'keyfile' in app and 'shortname' in app:
            for instanceid in range(0, conns):
                try:
                    apn = APNClient(app['environment'], app['certfile'], app['keyfile'], app['shortname'], instanceid)
                except Exception as ex:
                    logging.error(ex)
                    continue
                apnsconns[app['shortname']].append(apn)
        ''' GCMClient setup '''
        httpconns[app['shortname']] = []
        if 'gcmprojectnumber' in app and 'gcmapikey' in app and 'shortname' in app:
            try:
                http = GCMClient(app['gcmprojectnumber'], app['gcmapikey'], app['shortname'], 0)
            except Exception as ex:
                logging.error(ex)
                continue
            httpconns[app['shortname']].append(http)
    mongodb.close()
    return apnsconns, httpconns

if __name__ == "__main__":
    apnsconns, gcmconns = init_messaging_agents()
    (AirNotifierApp(apnsconnections=apnsconns, gcmconnections=gcmconns)).main()
