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

from pushservices.apns import APNClient
from pushservices.gcm import GCMClient
from pushservices.wns import WNSClient
from pushservices.mpns import MPNSClient
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

    def __init__(self, services):

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
        self.services = services

        handlers = self.init_routes()

        tornado.web.Application.__init__(self, handlers, **app_settings)

        mongodb = None
        while not mongodb:
            try:
                mongodb = Connection(options.mongohost, options.mongoport)
            except:
                error_log("Cannot not connect to MongoDB")

        self.mongodb = mongodb

        self.masterdb = mongodb[options.masterdb]
        assert self.masterdb.connection == self.mongodb
    def main(self):
        logging.info("Starting AirNotifier server")
        http_server = tornado.httpserver.HTTPServer(self)
        http_server.listen(options.port)
        logging.info("AirNotifier is running")
        try:
            tornado.ioloop.IOLoop.instance().start()
        except KeyboardInterrupt:
            logging.info("AirNotifier is quiting")
            tornado.ioloop.IOLoop.instance().stop()

def init_messaging_agents():
    services = {
            'gcm': {},
            'wns': {},
            'apns': {},
            'mpns': {},
            }
    mongodb = None
    while not mongodb:
        try:
            mongodb = Connection(options.mongohost, options.mongoport)
        except Exception as ex:
            logging.error(ex)
    masterdb = mongodb[options.masterdb]
    apps = masterdb.applications.find()
    for app in apps:
        ''' APNs setup '''
        services['apns'][app['shortname']] = []
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
                services['apns'][app['shortname']].append(apn)
        ''' GCMClient setup '''
        services['gcm'][app['shortname']] = []
        if 'gcmprojectnumber' in app and 'gcmapikey' in app and 'shortname' in app:
            try:
                http = GCMClient(app['gcmprojectnumber'], app['gcmapikey'], app['shortname'], 0)
            except Exception as ex:
                logging.error(ex)
                continue
            services['gcm'][app['shortname']].append(http)
        ''' WNS setup '''
        services['wns'][app['shortname']] = []
        if 'wnsclientid' in app and 'wnsclientsecret' in app and 'shortname' in app:
            try:
                wns = WNSClient(masterdb, app, 0)
            except Exception as ex:
                logging.error(ex)
                continue
            services['wns'][app['shortname']].append(wns)

        ''' MPNS setup '''
        services['mpns'][app['shortname']] = []
        if 'mpnsclientid' in app and 'mpnsclientsecret' in app and 'shortname' in app:
            try:
                mpns = MPNSClient(masterdb, app, 0)
            except Exception as ex:
                logging.error(ex)
                continue
            services['mpns'][app['shortname']].append(mpns)
    mongodb.close()
    return services

if __name__ == "__main__":
    tornado.options.parse_config_file("airnotifier.conf")
    tornado.options.parse_command_line()
    services = init_messaging_agents()
    AirNotifierApp(services=services).main()
