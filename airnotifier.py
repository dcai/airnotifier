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

import logging.config

from pymongo.connection import Connection
from tornado.options import define
import tornado.httpserver
import tornado.ioloop
import tornado.options

from pushservices.apns import *
from pushservices.gcm import GCMClient
from pushservices.wns import WNSClient
from pushservices.mpns import MPNSClient
from pushservices.clickatell import *
from uimodules import *
from util import *
from constants import DEVICE_TYPE_IOS, DEVICE_TYPE_ANDROID, DEVICE_TYPE_WNS, \
    DEVICE_TYPE_MPNS

define("port", default=8801, help="Application server listen port", type=int)

define("pemdir", default="pemdir", help="Directory to store pems")
define("passwordsalt", default="d2o0n1g2s0h3e1n1g", help="Being used to make password hash")
define("cookiesecret", default="airnotifiercookiesecret", help="Cookie secret")
define("debug", default=False, help="Debug mode")

define("https", default=False, help="Enable HTTPS")
define("httpscertfile", default="", help="HTTPS cert file")
define("httpskeyfile",  default="", help="HTTPS key file")

define("mongohost", default="localhost", help="MongoDB host name")
define("mongoport", default=27017, help="MongoDB port")

define("masterdb", default="airnotifier", help="MongoDB DB to store information")
define("collectionprefix", default="obj_", help="Collection name prefix")
define("dbprefix", default="app_", help="DB name prefix")
define("appprefix", default="", help="DB name prefix")

loggingconfigfile='logging.ini'
if os.path.isfile(loggingconfigfile):
    logging.config.fileConfig(loggingconfigfile)

_logger = logging.getLogger('AirNotifierApp')

class AirNotifierApp(tornado.web.Application):

    def init_routes(self, dir):
        from routes import RouteLoader
        return RouteLoader.load(dir)

    def get_broadcast_status(self, appname):
        status = "Notification sent!"
        error = False

        try:
            apns = self.services['apns'][appname][0]
        except (IndexError, KeyError):
            apns = None

        if apns is not None and apns.hasError():
            status = apns.getError()
            error = True

        return {'msg':status, 'error':error}

    def send_broadcast(self, appname, appdb, **kwargs):
        channel = kwargs.get('channel', 'default')
        alert   = kwargs.get('alert', None)
        sound   = kwargs.get('sound', None)
        badge   = kwargs.get('badge', None)
        device  = kwargs.get('device', None)
        extra   = kwargs.get('extra', {})
        try:
            apns = self.services['apns'][appname][0]
        except (IndexError, KeyError):
            apns = None
        try:
            wns = self.services['wns'][appname][0]
        except (IndexError, KeyError):
            wns = None
        try:
            mpns = self.services['mpns'][appname][0]
        except (IndexError, KeyError):
            mpns = None
        try:
            gcm = self.services['gcm'][appname][0]
        except (IndexError, KeyError):
            gcm = None

        conditions = []
        if channel == 'default':
            # channel is not set or channel is default
            conditions.append({'channel': {"$exists": False}})
            conditions.append({'channel': 'default'})
        else:
            conditions.append({'channel': channel})

        if device:
            conditions.append({'device': device})

        tokens = appdb.tokens.find({"$or": conditions})

        regids = []
        try:
            for token in tokens:
                t = token.get('token')
                if token['device'] == DEVICE_TYPE_IOS:
                    if apns is not None:
                        apns.process(token=t, alert=alert, extra=extra, apns=kwargs.get('apns', {}))
                elif token['device'] == DEVICE_TYPE_ANDROID:
                    regids.append(t)
                elif token['device'] == DEVICE_TYPE_WNS:
                    if wns is not None:
                        wns.process(token=t, alert=alert, extra=extra, wns=kwargs.get('wns', {}))
                elif token['device'] == DEVICE_TYPE_MPNS:
                    if mpns is not None:
                        mpns.process(token=t, alert=alert, extra=extra, mpns=kwargs.get('mpns', {}))
        except Exception as ex:
            _logger.error(ex)

        # Now sending android notifications
        try:
            if (gcm is not None) and regids:
                response = gcm.process(token=regids, alert=alert, extra=extra, gcm=kwargs.get('gcm', {}))
                responsedata = response.json()
        except Exception as ex:
            _logger.error('GCM problem: ' + str(ex))

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

        sitehandlers = self.init_routes('controllers')
        apihandlers = self.init_routes('api')

        tornado.web.Application.__init__(self, sitehandlers + apihandlers, **app_settings)

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
        _logger.info("Starting AirNotifier server")
        if options.https:
            import ssl
            try:
                ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ssl_ctx.load_cert_chain(options.httpscertfile, options.httpskeyfile)
            except IOError:
                print("Invalid path to SSL certificate and private key")
                raise
            http_server = tornado.httpserver.HTTPServer(self, ssl_options=ssl_ctx)
        else:
            http_server = tornado.httpserver.HTTPServer(self)
        http_server.listen(options.port)
        _logger.info("AirNotifier is ready")
        try:
            tornado.ioloop.IOLoop.instance().start()
        except KeyboardInterrupt:
            _logger.info("AirNotifier is quiting")
            tornado.ioloop.IOLoop.instance().stop()

def init_messaging_agents():
    services = {
            'gcm': {},
            'wns': {},
            'apns': {},
            'mpns': {},
            'sms': {},
            }
    mongodb = None
    while not mongodb:
        try:
            mongodb = Connection(options.mongohost, options.mongoport)
        except Exception as ex:
            _logger.error(ex)
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

        if file_exists(app.get('certfile', False)) and file_exists(app.get('keyfile', False)) and 'shortname' in app:
            if app.get('enableapns', False):
                for instanceid in range(0, conns):
                    try:
                        apn = APNClient(app['environment'], app['certfile'], app['keyfile'], app['shortname'], instanceid)
                    except Exception as ex:
                        _logger.error(ex)
                        continue
                    services['apns'][app['shortname']].append(apn)
        ''' GCMClient setup '''
        services['gcm'][app['shortname']] = []
        if 'gcmprojectnumber' in app and 'gcmapikey' in app and 'shortname' in app:
            try:
                http = GCMClient(app['gcmprojectnumber'], app['gcmapikey'], app['shortname'], 0)
            except Exception as ex:
                _logger.error(ex)
                continue
            services['gcm'][app['shortname']].append(http)
        ''' WNS setup '''
        services['wns'][app['shortname']] = []
        if 'wnsclientid' in app and 'wnsclientsecret' in app and 'shortname' in app:
            try:
                wns = WNSClient(masterdb, app, 0)
            except Exception as ex:
                _logger.error(ex)
                continue
            services['wns'][app['shortname']].append(wns)

        ''' MPNS setup '''
        services['mpns'][app['shortname']] = []
        try:
            mpns = MPNSClient(masterdb, app, 0)
        except Exception as ex:
            _logger.error(ex)
            continue
        services['mpns'][app['shortname']].append(mpns)
        ''' clickatell '''
        services['sms'][app['shortname']] = []
        try:
            sms = ClickatellClient(masterdb, app, 0)
        except Exception as ex:
            _logger.error(ex)
            continue
        services['sms'][app['shortname']].append(sms)
    mongodb.close()
    return services

if __name__ == "__main__":
    tornado.options.parse_config_file("airnotifier.conf")
    tornado.options.parse_command_line()
    services = init_messaging_agents()
    AirNotifierApp(services=services).main()
