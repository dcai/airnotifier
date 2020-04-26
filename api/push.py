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
from util import json_decode
import random
import time
import sys
from importlib import import_module
from constants import (
    DEVICE_TYPE_IOS,
    DEVICE_TYPE_ANDROID,
    DEVICE_TYPE_WNS,
    DEVICE_TYPE_FCM,
)
import logging
import traceback
import tornado


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

    async def post(self):
        try:
            """ Send notifications """
            if not self.can("send_notification"):
                self.send_response(
                    FORBIDDEN, dict(error="No permission to send notification")
                )
                return

            # if request body is json entity
            request_dict = json_decode(self.request.body)

            # application specific request_dict
            extra = request_dict.get("extra", {})
            # Hook
            if "processor" in extra:
                try:
                    proc = import_module("hooks." + extra["processor"])
                    request_dict = proc.process_pushnotification_payload(request_dict)
                except Exception as ex:
                    logging.error(str(ex))
                    self.send_response(BAD_REQUEST, dict(error=str(ex)))
                    return

            if not self.token:
                self.token = request_dict.get("token", None)

            device = request_dict.get("device", DEVICE_TYPE_FCM).lower()
            channel = request_dict.get("channel", "default")
            alert = request_dict.get("alert", "")
            token = self.dao.find_token(self.token)

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
                    self.dao.add_token(token)
                except Exception as ex:
                    logging.error(str(ex))
                    self.send_response(INTERNAL_SERVER_ERROR, dict(error=str(ex)))
                    return

            logging.info("sending notification to %s: %s" % (device, self.token))
            #  if device in [DEVICE_TYPE_FCM, DEVICE_TYPE_ANDROID]:
            if device.endswith(DEVICE_TYPE_FCM):
                fcm = request_dict.get("fcm", {})
                try:
                    fcmconn = self.fcmconnections[self.app["shortname"]][0]
                    await fcmconn.process(token=self.token, alert=alert, fcm=fcm)
                except Exception as ex:
                    statuscode = ex.code
                    # reference:
                    # https://firebase.google.com/docs/reference/fcm/rest/v1/ErrorCode
                    response_json = json_decode(ex.response.body)
                    logging.error(response_json)
                    self.add_to_log(
                        "error", tornado.escape.to_unicode(ex.response.body)
                    )
                    self.send_response(
                        statuscode, dict(error="error response from fcm")
                    )
                    return

            elif device == DEVICE_TYPE_IOS:
                # Use splitlines trick to remove line ending (only for iOS).
                if type(alert) is not dict:
                    alert = "".join(alert.splitlines())

                # https://developer.apple.com/library/archive/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/PayloadKeyReference.html#//apple_ref/doc/uid/TP40008194-CH17-SW1
                apns_default = {"badge": None, "sound": "default", "push_type": "alert"}
                apnspayload = request_dict.get("apns", {})
                conn = self.get_apns_conn()
                if conn:
                    try:
                        conn.process(
                            token=self.token,
                            alert=alert,
                            apns={**apns_default, **apnspayload},
                        )
                    except Exception as ex:
                        logging.error(ex)
                        self.send_response(400, dict(error="error response from apns"))
                        return
                else:
                    logging.error("no active apns connection")

            elif device == DEVICE_TYPE_WNS:
                request_dict.setdefault("wns", {})
                wns = self.wnsconnections[self.app["shortname"]][0]
                wns.process(
                    token=request_dict["token"],
                    alert=alert,
                    extra=extra,
                    wns=request_dict["wns"],
                )
            else:
                logging.error("invalid device type %s" % device)
                self.send_response(BAD_REQUEST, dict(error="Invalid device type"))
                return

            logmessage = "payload: %s, access key: %s" % (
                tornado.escape.to_unicode(self.request.body),
                self.appkey,
            )
            self.add_to_log("notification", logmessage)
            self.send_response(ACCEPTED)
        except Exception as ex:
            traceback_ex = traceback.format_exc()
            logging.error("%s %s" % (traceback_ex, str(ex)))
            self.send_response(INTERNAL_SERVER_ERROR, dict(error=str(ex)))
