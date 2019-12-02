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

from . import PushService
import requests
from tornado.httpclient import AsyncHTTPClient
import time
import xml.etree.ElementTree as ET

try:
    from io import StringIO
except:
    from io import StringIO

import logging

try:
    register_namespace = ET.register_namespace
except AttributeError:

    def register_namespace(prefix, uri):
        ET._namespace_map[uri] = prefix


class WNSException(Exception):
    pass


class WNSInvalidPushTypeException(WNSException):
    def __init__(self, type):
        Exception.__init__(self, "WNS Invalid push notification type :" + type)


WNSACCESSTOKEN_URL = "https://login.live.com/accesstoken.srf"


class WNSClient(PushService):
    def __init__(self, masterdb, app, instanceid=0):
        self.app = app
        self.masterdb = masterdb
        self.clientid = app["wnsclientid"]
        self.clientsecret = app["wnsclientsecret"]
        self.accesstoken = app["wnsaccesstoken"]
        self.tokentype = app["wnstokentype"]
        self.expiry = app["wnstokenexpiry"]

    def process(self, **kwargs):
        url = kwargs["token"]
        message = kwargs["alert"]
        now = int(time.time())
        wnsparams = kwargs["wns"]
        wnstype = wnsparams.get("type", "toast")

        accesstoken = self.accesstoken
        # if (not self.expiry) or self.expiry >= now:
        accesstoken = self.request_token()

        if wnstype not in ["toast", "tile", "badge", "raw"]:
            raise WNSInvalidPushTypeException(wnstype)

        if wnstype == "toast":
            wnsparams.setdefault("template", "ToastText01")
            wns = WNSToast(accesstoken=accesstoken)
        elif wnstype == "tile":
            wnsparams.setdefault("template", "TileSquare150x150Text01")
            wns = WNSTile(accesstoken=accesstoken)
        elif wnstype == "badge":
            wnsparams.setdefault("badge", {"value": None})
            wns = WNSTile(accesstoken=accesstoken)
        else:
            raise WNSInvalidPushTypeException(wnstype)
        wns.send(url, wnsparams)
        return

    def request_token(self):
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.clientid,
            "client_secret": self.clientsecret,
            "scope": "notify.windows.com",
        }
        response = requests.post(WNSACCESSTOKEN_URL, data=payload)
        responsedata = response.json()
        accesstoken = responsedata["access_token"]
        self.app["wnsaccesstoken"] = accesstoken
        self.app["wnstokenexpiry"] = int(responsedata["expires_in"]) + int(time.time())
        self.masterdb.applications.update(
            {"shortname": self.app["shortname"]}, self.app
        )
        return accesstoken


class WNSBase(object):

    HEADER_WNS_TYPE = "X-WNS-Type"
    HEADER_WNS_REQUESTFORSTATUS = "X-WNS-RequestForStatus"

    def __init__(self, accesstoken=None):
        self.accesstoken = accesstoken
        self.headers = {
            "Content-Type": "text/xml",
            "Authorization": "Bearer %s" % (self.accesstoken),
        }

    def set_type(self, target):
        self.headers[self.HEADER_WNS_TYPE] = "wns/%s" % target

    def serialize_tree(self, tree):
        file = StringIO()
        tree.write(file, encoding="utf-8")
        contents = "<?xml version='1.0' encoding='utf-8'?>" + file.getvalue()
        file.close()
        return contents

    def optional_attribute(self, element, attribute, payload_param, payload):
        if payload_param in payload:
            element.attrib["attribute"] = payload[payload_param]

    def optional_subelement(self, parent, element, payload_param, payload):
        if payload_param in payload:
            el = ET.SubElement(parent, element)
            el.text = payload[payload_param]
            return el

    def prepare_payload(self, payload):
        raise NotImplementedError("Subclasses should override prepare_payload method")

    def parse_response(self, response):
        status = {
            "deviceconnectionstatus": response.headers.get(
                "X-WNS-DeviceConnectionStatus", ""
            ),
            "error_description": response.headers.get("X-WNS-Error-Description", ""),
            "msgid": response.headers.get("X-WNS-Msg-ID", ""),
            "status": response.headers.get("X-WNS-Status", ""),
        }

        code = response.code
        status["http_status_code"] = code

        if code == 200:
            if status["status"] == "dropped":
                status["error"] = "dropped"
                status["backoff_seconds"] = 60
        elif code == 400:
            status["error"] = "Bad Request - invalid payload or subscription URI"
        elif code == 401:
            status["error"] = "Unauthorized - invalid token or subscription URI"
            status["drop_subscription"] = True
        elif code == 403:
            status[
                "error"
            ] = "The cloud service is not authorized to send a notification to this URI even though they are authenticated."
        elif code == 404:
            status[
                "error"
            ] = "The channel URI is not valid or is not recognized by WNS."
            status["drop_subscription"] = True
        elif code == 405:
            status["error"] = "Invalid Method"
        elif code == 503:
            status["error"] = "Service Unavailable - try again later"
            status["backoff_seconds"] = 60
        else:
            status["error"] = "Unexpected status"

        return status

    def handle_response(self, response):
        result = self.parse_response(response)
        # result['request'] = {'data': data, 'headers': dict(self.headers) }
        result["response"] = {
            "status": response.code,
            "headers": dict(response.headers),
            "text": response.body,
        }

    def send(self, uri, payload):
        """
        Send push message. Input parameters:

        uri - channel uri
        payload - message payload (see help for subclasses)
        accesstoken - token

        """
        data = self.prepare_payload(payload)
        http = AsyncHTTPClient()
        http.fetch(
            uri, self.handle_response, method="POST", headers=self.headers, body=data
        )


class WNSToast(WNSBase):
    def __init__(self, *args, **kwargs):
        super(WNSToast, self).__init__(*args, **kwargs)
        self.set_type("toast")

    def prepare_payload(self, payload):
        root = ET.Element("toast")
        visual = ET.SubElement(root, "visual")
        binding = ET.SubElement(visual, "binding")
        binding.attrib["template"] = payload["template"]
        if "text" in payload:
            count = 1
            for t in payload["text"]:
                el = ET.SubElement(binding, "text")
                el.text = t
                el.attrib["id"] = "%d" % count
                count = count + 1
        if "image" in payload:
            count = 1
            for image in payload["image"]:
                el = ET.SubElement(binding, "img")
                el.attrib["id"] = "%d" % count
                el.attrib["src"] = "%s" % image
                count = count + 1
        return self.serialize_tree(ET.ElementTree(root))


class WNSTile(WNSBase):
    def __init__(self, *args, **kwargs):
        super(WNSToast, self).__init__(*args, **kwargs)
        self.set_type("tile")

    def prepare_payload(self, payload):
        root = ET.Element("tile")
        visual = ET.SubElement(root, "visual")
        binding = ET.SubElement(visual, "binding")
        binding.attrib["template"] = payload["template"]
        if "text" in payload:
            count = 1
            for t in payload["text"]:
                el = ET.SubElement(binding, "text")
                el.text = t
                el.attrib["id"] = "%d" % count
                count = count + 1
        if "image" in payload:
            count = 1
            for image in payload["image"]:
                el = ET.SubElement(binding, "img")
                el.attrib["id"] = "%d" % count
                el.attrib["src"] = "%s" % image
                count = count + 1
        return self.serialize_tree(ET.ElementTree(root))


class WNSBadge(WNSBase):
    def __init__(self, *args, **kwargs):
        super(WNSToast, self).__init__(*args, **kwargs)
        self.set_type("badge")

    def prepare_payload(self, payload):
        root = ET.Element("badge")
        root.attrib["value"] = payload["badge"]["value"]
        return self.serialize_tree(ET.ElementTree(root))
