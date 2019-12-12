import logging
from .apns import *
from .clickatell import *
from .fcm import FCMClient
from .mpns import MPNSClient
from .wns import WNSClient
from constants import (
    DEVICE_TYPE_IOS,
    VERSION,
    KEY_APNS_AUTHKEY,
    KEY_APNS_BUNDLEID,
    KEY_APNS_KEYID,
    KEY_APNS_TEAMID,
    KEY_FCM_PROJECT_ID,
    KEY_FCM_JSON_KEY,
)


def init_messaging_agents(masterdb):

    services = {"apns": {}, "fcm": {}, "sms": {}, "wns": {}}

    apps = masterdb.applications.find()
    for app in apps:
        appname = app["shortname"]
        """ FCMClient setup """
        services["fcm"][appname] = []
        if KEY_FCM_JSON_KEY in app and KEY_FCM_PROJECT_ID in app:
            try:
                fcminstance = FCMClient(
                    project_id=app[KEY_FCM_PROJECT_ID],
                    jsonkey=app[KEY_FCM_JSON_KEY],
                    appname=appname,
                    instanceid=0,
                )
            except Exception as ex:
                import traceback

                traceback_ex = traceback.format_exc()
                logging.error("%s " % (traceback_ex))
                continue
            services["fcm"][appname].append(fcminstance)

        """ APNs setup """
        services["apns"][appname] = []

        try:
            apns = ApnsClient(
                auth_key=app[KEY_APNS_AUTHKEY],
                bundle_id=app[KEY_APNS_BUNDLEID],
                key_id=app[KEY_APNS_KEYID],
                team_id=app[KEY_APNS_TEAMID],
                appname=appname,
                instanceid=0,
            )
            services["apns"][appname].append(apns)
        except Exception as ex:
            logging.error(ex)
            continue

        """ WNS setup """
        services["wns"][appname] = []
        if "wnsclientid" in app and "wnsclientsecret" in app and "shortname" in app:
            try:
                wns = WNSClient(masterdb, app, 0)
            except Exception as ex:
                logging.error(ex)
                continue
            services["wns"][appname].append(wns)

    return services
