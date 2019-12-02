import logging
from .apns import *
from .clickatell import *
from .fcm import FCMClient
from .gcm import GCMClient
from .mpns import MPNSClient
from .wns import WNSClient


def init_messaging_agents(masterdb):

    services = {"apns": {}, "fcm": {}, "sms": {}, "wns": {}}

    apps = masterdb.applications.find()
    for app in apps:
        """ FCMClient setup """
        services["fcm"][app["shortname"]] = []
        if "fcm-project-id" in app and "fcm-jsonkey" in app:
            try:
                fcminstance = FCMClient(
                    project_id=app["fcm-project-id"],
                    jsonkey=app["fcm-jsonkey"],
                    appname=app["shortname"],
                    instanceid=0,
                )
            except Exception as ex:
                import traceback

                traceback_ex = traceback.format_exc()
                logging.error("%s " % (traceback_ex))
                continue
            services["fcm"][app["shortname"]].append(fcminstance)

        """ APNs setup """
        services["apns"][app["shortname"]] = []
        conns = int(app["connections"])
        if conns < 1:
            conns = 1
        if "environment" not in app:
            app["environment"] = "sandbox"

        if (
            file_exists(app.get("certfile", False))
            and file_exists(app.get("keyfile", False))
            and "shortname" in app
        ):
            if app.get("enableapns", False):
                for instanceid in range(0, conns):
                    try:
                        apn = APNClient(
                            app["environment"],
                            app["certfile"],
                            app["keyfile"],
                            app["shortname"],
                            instanceid,
                        )
                    except Exception as ex:
                        logging.error(ex)
                        continue
                    services["apns"][app["shortname"]].append(apn)

        """ WNS setup """
        services["wns"][app["shortname"]] = []
        if "wnsclientid" in app and "wnsclientsecret" in app and "shortname" in app:
            try:
                wns = WNSClient(masterdb, app, 0)
            except Exception as ex:
                logging.error(ex)
                continue
            services["wns"][app["shortname"]].append(wns)

    return services
