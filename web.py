from constants import (
    DEVICE_TYPE_ANDROID,
    DEVICE_TYPE_FCM,
    DEVICE_TYPE_IOS,
    DEVICE_TYPE_WNS,
    RELEASE,
    VERSION,
)
from uimodules import *
import datetime
import os
import logging
import tornado
import tornado.httpserver
import tornado.ioloop


class NotFoundHandler(tornado.web.RequestHandler):
    def prepare(self):  # for all methods
        self.set_status(404, None)
        self.finish()


class WebApplication(tornado.web.Application):
    def __init__(self, container):
        self.container = container
        self.services = container.services
        self.mongodb = container.mongodbconn
        options = container.serveroptions
        self.masterdb = self.mongodb[options.masterdb]

        now = datetime.datetime.now()

        app_settings = dict(
            debug=options.debug,
            app_title="AirNotifier",
            current_year=str(now.year),
            version="{}-{}".format(RELEASE, VERSION),
            ui_modules={"AppSideBar": AppSideBar, "NavBar": NavBar, "TabBar": TabBar},
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret=options.cookiesecret,
            login_url=r"/auth/login",
            autoescape=None,
            default_handler_class=NotFoundHandler,
        )

        sitehandlers = self.init_routes("controllers")
        apihandlers = self.init_routes("api")

        tornado.web.Application.__init__(
            self, sitehandlers + apihandlers, **app_settings
        )

    def init_routes(self, dir):
        from routes import RouteLoader

        return RouteLoader.load(dir)

    def get_broadcast_status(self, appname):
        status = "Notification sent!"
        error = False

        try:
            apns = self.services["apns"][appname][0]
        except (IndexError, KeyError):
            apns = None

        if apns is not None and apns.hasError():
            status = apns.getError()
            error = True

        return {"msg": status, "error": error}

    async def send_broadcast(self, appname, appdb, **kwargs):
        channel = kwargs.get("channel", "default")
        alert = kwargs.get("alert", None)
        sound = kwargs.get("sound", None)
        badge = kwargs.get("badge", None)
        device = kwargs.get("device", None)
        extra = kwargs.get("extra", {})
        try:
            apns = self.services["apns"][appname][0]
        except (IndexError, KeyError):
            apns = None
        try:
            wns = self.services["wns"][appname][0]
        except (IndexError, KeyError):
            wns = None
        try:
            fcm = self.services["fcm"][appname][0]
        except (IndexError, KeyError):
            fcm = None

        conditions = []
        if channel == "default":
            # channel is not set or channel is default
            conditions.append({"channel": {"$exists": False}})
            conditions.append({"channel": "default"})
        else:
            conditions.append({"channel": channel})

        if device:
            conditions.append({"device": device})

        tokens = appdb.tokens.find({"$or": conditions})

        regids = []
        try:
            for token in tokens:
                t = token.get("token")
                if token["device"] == DEVICE_TYPE_IOS:
                    if apns is not None:
                        apns.process(
                            token=t,
                            alert=alert,
                            extra=extra,
                            apns=kwargs.get("apns", {}),
                        )
                elif token["device"] == DEVICE_TYPE_FCM or token["device"] == DEVICE_TYPE_ANDROID:
                    await fcm.process(
                        token=t, alert=alert, extra=extra, fcm=kwargs.get("fcm", {})
                    )
                elif token["device"] == DEVICE_TYPE_WNS:
                    if wns is not None:
                        wns.process(
                            token=t, alert=alert, extra=extra, wns=kwargs.get("wns", {})
                        )
        except Exception as ex:
            logging.error(ex)

    def main(self):
        options = self.container.serveroptions
        if options.https:
            import ssl

            try:
                ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ssl_ctx.load_cert_chain(options.httpscertfile, options.httpskeyfile)
            except IOError:
                logging.error("Invalid path to SSL certificate and private key")
                raise
            http_server = tornado.httpserver.HTTPServer(self, ssl_options=ssl_ctx)
        else:
            http_server = tornado.httpserver.HTTPServer(self, xheaders=True)
        http_server.listen(options.port)
        logging.info("AirNotifier is listening at port: %s" % options.port)
        try:
            tornado.ioloop.IOLoop.instance().start()
        except KeyboardInterrupt:
            logging.info("AirNotifier is quiting")
            self.mongodb.close()
            tornado.ioloop.IOLoop.instance().stop()
