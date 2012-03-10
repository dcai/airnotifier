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

import logging
import tornado.auth
import tornado.httpserver
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import json
import oauth
import test

from apns import *
from tornado.options import define, options

define("certfile", default="cert.pem", help="Certificate file")
define("keyfile", default="key.pem", help="Private key file")
define("disableapns", default=False, help="Not using APNs")
define("apns", default=(), help="APNs")

logging.getLogger().setLevel(logging.INFO)

class BaseHandler(tornado.web.RequestHandler):

    """BaseHandler class

    The BaseHandler includes a few common methods

    TODO: needs to handle:
    - X-AN-APP-ID: 1
    - X-AN-APP-KEY: XXX
    """

    def send_response(self, data=None):
        """ Set REST API response """

        self.set_header('Content-Type',
                        'application/json; charset=utf-8')
        self.set_header('X-Powered-By', 'AirNotifier/1.0')
        if data:
            jsontext = json.dumps(data)
            self.finish(jsontext)
        else:
            self.finish()

    def get_current_user(self):
        """ Get current user from cookie """

        user_json = self.get_secure_cookie('user')
        if not user_json:
            return None
        return tornado.escape.json_decode(user_json)


class MainHandler(BaseHandler):

    def get(self):
        self.redirect(r"/applications/")

    def head(self):
        self.send_response(None)


class NotificationHandler(BaseHandler):

    def get(self):
        self.finish('Move along')

    def post(self):
        token = self.get_argument('devicetoken')
        if len(token) != 64:
            self.send_response(dict(error='Invalid token'))
            return
        alert = self.get_argument('alert')
        sound = self.get_argument('sound', 'default')
        badge = int(self.get_argument('badge', 0))
        pl = PayLoad(alert=alert, sound=sound, badge=1)
        try:
            apn.send(token, pl)
            self.send_response(dict(status='ok'))
        except Exception, ex:
            self.send_response(dict(error=str(ex)))


class AuthHandler(BaseHandler, tornado.auth.GoogleMixin):

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


class LogoutHandler(BaseHandler):

    def get(self):
        self.clear_cookie('user')
        self.redirect(r"/")


class AppHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):
        fullname = tornado.escape.xhtml_escape(self.current_user['name'])
        self.oauth_server = oauth.OAuthServer()
        self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_PLAINTEXT())
        self.oauth_server.add_signature_method(oauth.OAuthSignatureMethod_HMAC_SHA1())
        self.render('apps.html')

class UserHandler(BaseHandler):
    """Handle users
    - Take application ID and secret
    - Create user
    """
    def post(self):
        """ Create user """
        pass
    def get(self):
        """Get user info
        supply loggged token to get private info
        """
        pass
    def delete(self):
        """ Delete user """
        pass
    def put(self):
        """ Update """
        pass

class ObjectHandler(BaseHandler):
    """Object Handler
    http://airnotifier.xxx/objects/option/1
    option will be the resource name
    """
    def get(self):
        """Query resource
        """
        pass
    def post(self):
        """Create object
        """
        pass

class AdminHandler(object):
    pass

class AirNotifierApp(tornado.web.Application):

    def __init__(self):
        app_settings = dict(
            debug=True,
            app_title=u'AirNotifier',
            template_path=os.path.join(os.path.dirname(__file__),
                    'templates'),
            static_path=os.path.join(os.path.dirname(__file__), 'static'
                    ),
            cookie_secret='airnotifiercookie',
            login_url=r"/auth/login",
            )
        handlers = [(r"/", MainHandler),
                    (r"/notification/", NotificationHandler),
                    (r"/users/", UserHandler),
                    (r"/objects/", ObjectHandler),
                    (r"/applications/", AppHandler),
                    # Admin
                    (r"/admin/", AdminHandler),
                    # authentication session
                    (r"/auth/login", AuthHandler),
                    (r"/auth/logout", LogoutHandler),
                    ]

        tornado.web.Application.__init__(self, handlers, **app_settings)


if __name__ == "__main__":
    tornado.options.parse_config_file("airnotifier.conf")
    tornado.options.parse_command_line()
    logging.info("Starting AirNotifier server")
    if options.disableapns is not True:
        apn = APNClient(options.apns, options.certfile, options.keyfile)
    http_server = tornado.httpserver.HTTPServer(AirNotifierApp())
    http_server.listen(8000)
    tornado.ioloop.IOLoop.instance().start()
