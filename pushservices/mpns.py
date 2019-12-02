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
import logging
from tornado.options import options
import os.path
from tornado.httpclient import AsyncHTTPClient
from util import *
import xml.etree.ElementTree as ET

try:
    from io import StringIO
except:
    from io import StringIO

try:
    register_namespace = ET.register_namespace
except AttributeError:

    def register_namespace(prefix, uri):
        ET._namespace_map[uri] = prefix


class MPNSClient(PushService):
    def __init__(self, masterdb, app, instanceid=0):
        self.app = app
        self.masterdb = masterdb

    def process(self, **kwargs):
        uri = kwargs["token"]
        message = kwargs["alert"]
        mpnsparams = kwargs["mpns"]
        mpnstype = "toast"
        if "type" in mpnsparams:
            mpnstype = mpnsparams["type"]
        if mpnstype == "toast":
            mpns = MPNSToast()
            if "text1" not in mpnsparams:
                mpnsparams["text1"] = message
        elif mpnstype == "tile":
            mpns = MPNSTile()
        cert = get_filepath(self.app.get("mpnscertificatefile", ""))
        mpns.send(uri, mpnsparams, cert=cert)


# https://github.com/max-arnold/python-mpns
#
# Copyright (c) 2013, DM Group LLC
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright
#  notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright
#  notice, this list of conditions and the following disclaimer in the
#  documentation and/or other materials provided with the distribution.
# * Neither the name of the "DM Group LLC" nor the names of its
#  contributors may be used to endorse or promote products derived
#  from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL "DM Group LLC" BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# https://raw.githubusercontent.com/max-arnold/python-mpns/master/mpns/notification.py


class MPNSBase(object):
    DELAY_IMMEDIATE = None
    DELAY_450S = None
    DELAY_900S = None

    HEADER_NOTIFICATION_CLASS = "X-NotificationClass"
    HEADER_TARGET = "X-WindowsPhone-Target"
    HEADER_MESSAGE_ID = "X-MessageID"
    HEADER_CALLBACK_URI = "X-CallbackURI"

    def __init__(self, delay=None):
        self.delay = delay or self.DELAY_IMMEDIATE
        self.headers = {
            "Content-Type": "text/xml",
            "Accept": "application/*",
            self.HEADER_NOTIFICATION_CLASS: str(self.delay),
        }
        register_namespace("wp", "WPNotification")

    def set_target(self, target):
        self.headers[self.HEADER_TARGET] = target

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
            "device_connection_status": response.headers.get(
                "x-deviceconnectionstatus", ""
            ),  # Connected, InActive, Disconnected, TempDisconnected
            "subscription_status": response.headers.get(
                "x-subscriptionstatus", ""
            ),  # Active, Expired
            "notification_status": response.headers.get(
                "x-notificationstatus", ""
            ),  # Received, Suppressed, Dropped, QueueFull
            "message_id": response.headers.get(
                "x-messageid"
            ),  # 00000000-0000-0000-0000-000000000000
        }

        code = response.code
        status["http_status_code"] = code

        if code == 200:
            if status["notification_status"] == "QueueFull":
                status["error"] = "Queue full, try again later"
                status["backoff_seconds"] = 60
        elif code == 400:
            status["error"] = "Bad Request - invalid payload or subscription URI"
        elif code == 401:
            status["error"] = "Unauthorized - invalid token or subscription URI"
            status["drop_subscription"] = True
        elif code == 404:
            status["error"] = "Not Found - subscription URI is invalid"
            status["drop_subscription"] = True
        elif code == 405:
            status[
                "error"
            ] = (
                "Invalid Method"
            )  # (this should not happen, module uses only POST method)
        elif code == 406:
            status["error"] = "Not Acceptable - per-day throttling limit reached"
            status["backoff_seconds"] = 24 * 60 * 60
        elif code == 412:
            status["error"] = "Precondition Failed - device inactive, try once per-hour"
            status["backoff_seconds"] = 60 * 60
        elif code == 503:
            status["error"] = "Service Unavailable - try again later"
            status["backoff_seconds"] = 60
        else:
            status["error"] = "Unexpected status"

        return status

    def send(
        self, uri, payload, message_id=None, callback_uri=None, cert=None, debug=False
    ):
        """
        Send push message. Input parameters:

        uri - subscription uri
        payload - message payload (see help for subclasses)
        message_id - optional message id (UUID)
        callback_uri - optional callback url (only for authenticated web services)
        cert - optional (only for authenticated web services)
            If string, path to ssl client cert file (.pem).
            If tuple, (‘cert’, ‘key’) pair.
            For more info see requests library documentation.

        Returns message status dictionary with the following elements:

        device_connection_status - Connected, InActive, Disconnected, TempDisconnected
        subscription_status - Active, Expired
        notification_status - Received, Suppressed, Dropped, QueueFull
        message_id - submitted message_id or 00000000-0000-0000-0000-000000000000
        http_status_code - HTTP response status code
        error - optional error message
        backoff_seconds - optional recommended throttling delay (in seconds)
        drop_subscription - optional flag to indicate that subscription uri is invalid
        """
        if not cert:
            cert = None

        # reset per-message headers
        for k in (self.HEADER_MESSAGE_ID, self.HEADER_CALLBACK_URI):
            if k in self.headers:
                self.headers.pop(k)

        # set per-message headers if necessary
        if message_id:
            self.headers[self.HEADER_MESSAGE_ID] = str(
                message_id
            )  # TODO: validate UUID

        if callback_uri:
            self.headers[self.HEADER_CALLBACK_URI] = str(callback_uri)

        data = self.prepare_payload(payload)

        http = AsyncHTTPClient()
        if not file_exists(cert):
            cert = None

        http.fetch(
            uri,
            self.handle_response,
            method="POST",
            headers=self.headers,
            body=data,
            ca_certs=cert,
        )

    def handle_response(self, response):
        result = self.parse_response(response)
        # result['request'] = {'data': data, 'headers': dict(self.headers) }
        result["response"] = {
            "status": response.code,
            "headers": dict(response.headers),
            "text": response.body,
        }


# TODO: create separate classes for FlipTile, Cycle and Iconic notifications (also add version 2.0)
# WP8 specific:
# self.clearable_subelement(tile, '{WPNotification}SmallBackgroundImage' 'small_background_image', payload)
# self.clearable_subelement(tile, '{WPNotification}WideBackgroundImage' 'wide_background_image', payload)
# self.clearable_subelement(tile, '{WPNotification}WideBackBackgroundImage' 'wide_back_background_image', payload)
# self.clearable_subelement(tile, '{WPNotification}WideBackContent' 'wide_back_content', payload)
class MPNSTile(MPNSBase):
    """
    Tile notification. Payload is a dictionary with the following optional elements:

    id
    template
    background_image
    count
    title
    back_background_image
    back_title
    back_content
    """

    DELAY_IMMEDIATE = 1
    DELAY_450S = 11
    DELAY_900S = 21

    def __init__(self, *args, **kwargs):
        super(MPNSTile, self).__init__(*args, **kwargs)
        self.set_target("token")  # TODO: flip tile

    def clearable_subelement(self, parent, element, payload_param, payload):
        if payload_param in payload:
            el = ET.SubElement(parent, element)
            if payload[payload_param] is None:
                el.attrib["Action"] = "Clear"
            else:
                el.text = payload[payload_param]
            return el

    def prepare_payload(self, payload):
        root = ET.Element("{WPNotification}Notification")
        tile = ET.SubElement(root, "{WPNotification}Tile")
        self.optional_attribute(tile, "Id", "id", payload)
        self.optional_attribute(tile, "Template", "template", payload)
        self.optional_subelement(
            tile, "{WPNotification}BackgroundImage", "background_image", payload
        )
        self.clearable_subelement(tile, "{WPNotification}Count", "count", payload)
        self.clearable_subelement(tile, "{WPNotification}Title", "title", payload)
        self.clearable_subelement(
            tile,
            "{WPNotification}BackBackgroundImage",
            "back_background_image",
            payload,
        )
        self.clearable_subelement(
            tile, "{WPNotification}BackTitle", "back_title", payload
        )
        self.clearable_subelement(
            tile, "{WPNotification}BackContent", "back_content", payload
        )
        return self.serialize_tree(ET.ElementTree(root))


class MPNSToast(MPNSBase):
    """
    Toast notification. Payload is a dictionary with the following optional elements:

    text1
    text2
    param
    """

    DELAY_IMMEDIATE = 2
    DELAY_450S = 12
    DELAY_900S = 22

    def __init__(self, *args, **kwargs):
        super(MPNSToast, self).__init__(*args, **kwargs)
        self.set_target("toast")

    def prepare_payload(self, payload):
        root = ET.Element("{WPNotification}Notification")
        toast = ET.SubElement(root, "{WPNotification}Toast")
        self.optional_subelement(toast, "{WPNotification}Text1", "text1", payload)
        self.optional_subelement(toast, "{WPNotification}Text2", "text2", payload)
        self.optional_subelement(
            toast, "{WPNotification}Param", "param", payload
        )  # TODO: validate param (/ and length)
        return self.serialize_tree(ET.ElementTree(root))


class MPNSRaw(MPNSBase):
    """
    Raw notification. Payload format can be arbitrary.
    """

    DELAY_IMMEDIATE = 3
    DELAY_450S = 13
    DELAY_900S = 23

    def __init__(self, *args, **kwargs):
        super(MPNSRaw, self).__init__(*args, **kwargs)
        self.set_target("raw")

    def prepare_payload(self, payload):
        return payload
