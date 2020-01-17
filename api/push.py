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

from http.client import BAD_REQUEST, FORBIDDEN, INTERNAL_SERVER_ERROR, ACCEPTED
from routes import route
from api import APIBaseHandler, EntityBuilder
from util import json_decode, json_encode
import random
import time, sys
from importlib import import_module
from constants import (
    DEVICE_TYPE_IOS,
    DEVICE_TYPE_ANDROID,
    DEVICE_TYPE_WNS,
    DEVICE_TYPE_FCM,
)
import logging

_logger = logging.getLogger(__name__)


@route(r"/api/v2/push[\/]?")
class PushHandler(APIBaseHandler):
    def get_apns_conn(self):
        if self.app["shortname"] not in self.apnsconnections:
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
            requestPayload = json_decode(self.request.body)

            # application specific requestPayload
            extra = requestPayload.get("extra", {})
            # Hook
            if "processor" in extra:
                try:
                    proc = import_module("hooks." + extra["processor"])
                    requestPayload = proc.process_pushnotification_payload(
                        requestPayload
                    )
                except Exception as ex:
                    self.send_response(BAD_REQUEST, dict(error=str(ex)))
                    return

            if not self.token:
                self.token = requestPayload.get("token", None)

            device = requestPayload.get("device", DEVICE_TYPE_FCM).lower()
            channel = requestPayload.get("channel", "default")
            alert = requestPayload.get("alert", "")
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
                    return

            #  if device in [DEVICE_TYPE_FCM, DEVICE_TYPE_ANDROID]:
            if device.endswith(DEVICE_TYPE_FCM):
                fcm_payload = requestPayload.get("fcm", {})
                try:
                    fcmconn = self.fcmconnections[self.app["shortname"]][0]
                    response = fcmconn.process(
                        token=self.token, alert=alert, extra=extra, fcm=fcm_payload
                    )
                except Exception as ex:
                    self.send_response(INTERNAL_SERVER_ERROR, dict(error=str(ex)))
                    return

            elif device == DEVICE_TYPE_IOS:
                # Use splitlines trick to remove line ending (only for iOS).
                if type(alert) is not dict:
                    alert = "".join(alert.splitlines())

                apns_default = {
                    "badge": None,
                    "sound": None,
                    "content": None,
                    "custom": None,
                }
                apns = {**apns_default, **requestPayload["apns"]}
                conn = self.get_apns_conn()
                if conn:
                    conn.process(token=self.token, alert=alert, extra=extra, apns=apns)
                else:
                    _logger.error("no active apns connection")
            elif device == DEVICE_TYPE_WNS:
                requestPayload.setdefault("wns", {})
                wns = self.wnsconnections[self.app["shortname"]][0]
                wns.process(
                    token=requestPayload["token"],
                    alert=alert,
                    extra=extra,
                    wns=requestPayload["wns"],
                )
            else:
                self.send_response(BAD_REQUEST, dict(error="Invalid device type"))
                return

            logmessage = "payload: %s, access key: %s" % (
                self.request.body.encode("utf-8"),
                self.appkey,
            )
            self.add_to_log("notification", logmessage)
            self.send_response(ACCEPTED)
        except Exception as ex:
            import traceback

            traceback.print_exc()
            self.send_response(INTERNAL_SERVER_ERROR, dict(error=str(ex)))
