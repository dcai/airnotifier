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

from http.client import BAD_REQUEST, FORBIDDEN, NOT_FOUND, INTERNAL_SERVER_ERROR, OK
from routes import route
from api import APIBaseHandler, EntityBuilder
from constants import DEVICE_TYPE_IOS, DEVICE_TYPE_FCM
import binascii
import logging
from util import json_decode


@route(r"/api/v2/tokens/([^/]+)")
class TokenV2HandlerGet(APIBaseHandler):
    def delete(self, token):
        """Delete a token
        """
        # To check the access key permissions we use bitmask method.
        if not self.can("delete_token"):
            self.send_response(FORBIDDEN, dict(error="No permission to delete token"))
            return

        try:
            result = self.db.tokens.remove({"token": token})
            if result["n"] == 0:
                self.send_response(NOT_FOUND, dict(status="Token does't exist"))
            else:
                self.send_response(OK, dict(status="deleted"))
        except Exception as ex:
            self.send_response(INTERNAL_SERVER_ERROR, dict(error=str(ex)))


@route(r"/api/v2/tokens[\/]?")
class TokenV2Handler(APIBaseHandler):
    def post(self):
        """Create a new token
        """
        if not self.can("create_token"):
            self.send_response(FORBIDDEN, dict(error="No permission to create token"))
            return

        data = json_decode(self.request.body)

        device = data.get("device", DEVICE_TYPE_FCM).lower()
        channel = data.get("channel", "default")
        devicetoken = data.get("token", "")

        if device == DEVICE_TYPE_IOS:
            if len(devicetoken) != 64:
                self.send_response(BAD_REQUEST, dict(error="Invalid token"))
                return
            try:
                binascii.unhexlify(devicetoken)
            except Exception as ex:
                self.send_response(BAD_REQUEST, dict(error="Invalid token"))

        token = EntityBuilder.build_token(devicetoken, device, self.appname, channel)
        try:
            result = self.db.tokens.update(
                {"device": device, "token": devicetoken, "appname": self.appname},
                token,
                upsert=True,
            )
            # result
            # {u'updatedExisting': True, u'connectionId': 47, u'ok': 1.0, u'err': None, u'n': 1}
            if result["updatedExisting"]:
                self.add_to_log("Token exists", devicetoken)
                self.send_response(OK)
            else:
                self.add_to_log("Add token", devicetoken)
                self.send_response(OK)
        except Exception as ex:
            self.send_response(INTERNAL_SERVER_ERROR, dict(error=str(ex)))
