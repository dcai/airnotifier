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

try:
    from httplib import BAD_REQUEST, FORBIDDEN, INTERNAL_SERVER_ERROR, ACCEPTED
except:
    from http.client import BAD_REQUEST, FORBIDDEN, INTERNAL_SERVER_ERROR, ACCEPTED
from routes import route
from api import APIBaseHandler, EntityBuilder
import random
import time
from importlib import import_module
from constants import (
    DEVICE_TYPE_IOS,
    DEVICE_TYPE_ANDROID,
    DEVICE_TYPE_WNS,
    DEVICE_TYPE_MPNS,
    DEVICE_TYPE_SMS,
    DEVICE_TYPE_FCM,
)
from pushservices.gcm import (
    GCMUpdateRegIDsException,
    GCMInvalidRegistrationException,
    GCMNotRegisteredException,
    GCMException,
)
from pushservices.fcm import FCMException
import logging

_logger = logging.getLogger(__name__)


@route(r"/api/v2/push[\/]?")
class PushHandler(APIBaseHandler):
    def validate_payload(self, payload):
        payload.setdefault("channel", "default")
        payload.setdefault("sound", None)
        payload.setdefault("badge", None)
        payload.setdefault("extra", {})
        return payload

    def get_apns_conn(self):
        if not self.apnsconnections.has_key(self.app["shortname"]):
            self.send_response(INTERNAL_SERVER_ERROR, dict(error="APNs is offline"))
            return
        count = len(self.apnsconnections[self.app["shortname"]])
        # Find an APNS instance
        random.seed(time.time())
        if count > 0:
            instanceid = random.randint(0, count - 1)
            return self.apnsconnections[self.app["shortname"]][instanceid]

    def post(self):
        try:
            """ Send notifications """
            if not self.can("send_notification"):
                self.send_response(
                    FORBIDDEN, dict(error="No permission to send notification")
                )
                return

            # if request body is json entity
            requestPayload = self.json_decode(self.request.body)
            requestPayload = self.validate_payload(requestPayload)

            # Hook
            if "extra" in requestPayload:
                if "processor" in requestPayload["extra"]:
                    try:
                        proc = import_module(
                            "hooks." + requestPayload["extra"]["processor"]
                        )
                        requestPayload = proc.process_pushnotification_payload(
                            requestPayload
                        )
                    except Exception as ex:
                        self.send_response(BAD_REQUEST, dict(error=str(ex)))

            if not self.token:
                self.token = requestPayload.get("token", None)

            # application specific requestPayload
            extra = requestPayload.get("extra", {})

            device = requestPayload.get("device", DEVICE_TYPE_IOS).lower()
            channel = requestPayload.get("channel", "default")
            token = self.db.tokens.find_one({"token": self.token})

            if not token:
                token = EntityBuilder.build_token(
                    self.token, device, self.appname, channel
                )
                if not self.can("create_token"):
                    self.send_response(
                        BAD_REQUEST,
                        dict(error="Unknow token and you have no permission to create"),
                    )
                    return
                try:
                    # TODO check permission to insert
                    self.db.tokens.insert(token)
                except Exception as ex:
                    self.send_response(INTERNAL_SERVER_ERROR, dict(error=str(ex)))

            if device == DEVICE_TYPE_SMS:
                requestPayload.setdefault("sms", {})
                requestPayload["sms"].setdefault("to", requestPayload.get("token", ""))
                requestPayload["sms"].setdefault(
                    "message", requestPayload.get("message", "")
                )
                sms = self.smsconnections[self.app["shortname"]][0]
                sms.process(
                    token=requestPayload["token"],
                    alert=requestPayload["alert"],
                    extra=extra,
                    sms=requestPayload["sms"],
                )
                self.send_response(ACCEPTED)
            elif device == DEVICE_TYPE_IOS:

                # Use splitlines trick to remove line ending (only for iOS).
                if type(requestPayload["alert"]) is not dict:
                    alert = "".join(requestPayload["alert"].splitlines())
                else:
                    alert = requestPayload["alert"]
                requestPayload.setdefault("apns", {})
                requestPayload["apns"].setdefault(
                    "badge", requestPayload.get("badge", None)
                )
                requestPayload["apns"].setdefault(
                    "sound", requestPayload.get("sound", None)
                )
                requestPayload["apns"].setdefault(
                    "content", requestPayload.get("content", None)
                )
                requestPayload["apns"].setdefault(
                    "custom", requestPayload.get("custom", None)
                )
                conn = self.get_apns_conn()
                if conn:
                    conn.process(
                        token=self.token,
                        alert=alert,
                        extra=extra,
                        apns=requestPayload["apns"],
                    )
                else:
                    _logger.error("no active apns connection")
                self.send_response(ACCEPTED)
            elif device == DEVICE_TYPE_FCM:
                requestPayload.setdefault("fcm", {})
                try:
                    fcm = self.fcmconnections[self.app["shortname"]][0]
                    response = fcm.process(
                        token=self.token,
                        alert=requestPayload["alert"],
                        extra=requestPayload["extra"],
                        fcm=requestPayload["fcm"],
                    )
                    self.send_response(ACCEPTED)
                except FCMException as ex:
                    self.send_response(INTERNAL_SERVER_ERROR, dict(error=ex.error))
            elif device == DEVICE_TYPE_ANDROID:
                requestPayload.setdefault("gcm", {})
                try:
                    gcm = self.gcmconnections[self.app["shortname"]][0]
                    response = gcm.process(
                        token=[self.token],
                        alert=requestPayload["alert"],
                        extra=requestPayload["extra"],
                        gcm=requestPayload["gcm"],
                    )
                    responserequestPayload = response.json()
                    if responserequestPayload["failure"] == 0:
                        self.send_response(ACCEPTED)
                except GCMUpdateRegIDsException as ex:
                    self.send_response(ACCEPTED)
                except GCMInvalidRegistrationException as ex:
                    self.send_response(
                        BAD_REQUEST, dict(error=str(ex), regids=ex.regids)
                    )
                except GCMNotRegisteredException as ex:
                    self.send_response(
                        BAD_REQUEST, dict(error=str(ex), regids=ex.regids)
                    )
                except GCMException as ex:
                    self.send_response(INTERNAL_SERVER_ERROR, dict(error=str(ex)))
            elif device == DEVICE_TYPE_WNS:
                requestPayload.setdefault("wns", {})
                wns = self.wnsconnections[self.app["shortname"]][0]
                wns.process(
                    token=requestPayload["token"],
                    alert=requestPayload["alert"],
                    extra=extra,
                    wns=requestPayload["wns"],
                )
                self.send_response(ACCEPTED)
            elif device == DEVICE_TYPE_MPNS:
                requestPayload.setdefault("mpns", {})
                mpns = self.mpnsconnections[self.app["shortname"]][0]
                mpns.process(
                    token=requestPayload["token"],
                    alert=requestPayload["alert"],
                    extra=extra,
                    mpns=requestPayload["mpns"],
                )
                self.send_response(ACCEPTED)
            else:
                self.send_response(BAD_REQUEST, dict(error="Invalid device type"))
                logmessage = "Message length: %s, Access key: %s" % (
                    len(requestPayload["alert"]),
                    self.appkey,
                )
                self.add_to_log("%s notification" % self.appname, logmessage)
        except Exception as ex:
            import traceback

            traceback.print_exc()
            self.send_response(INTERNAL_SERVER_ERROR, dict(error=str(ex)))
