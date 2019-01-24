#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Server Side FCM sample.

Firebase Cloud Messaging (FCM) can be used to send messages to clients on iOS,
Android and Web.

This sample uses FCM to send two types of messages to clients that are subscribed
to the `news` topic. One type of message is a simple notification message (display message).
The other is a notification message (display notification) with platform specific
customizations. For example, a badge is added to messages that are sent to iOS devices.
"""

import argparse
import json
import requests
from . import PushService
import json
import time
from util import strip_tags
import logging

_logger = logging.getLogger("fcm")


class FCMException(Exception):
    def __init__(self, error):
        self.error = error


from oauth2client.service_account import ServiceAccountCredentials

BASE_URL = "https://fcm.googleapis.com"
SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]


class FCMClient(PushService):
    def __init__(self, project_id, jsonkey, appname, instanceid=0):
        self.project_id = project_id
        self.jsonkey = jsonkey
        self.appname = appname
        self.instanceid = instanceid
        jsonData = json.loads(jsonkey)
        self.credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            jsonData, SCOPES
        )
        self.endpoint = "%s/v1/projects/%s/messages:send" % (BASE_URL, self.project_id)

    def build_request(self, token, alert):
        payload = {
            "message": {"token": token, "notification": {"body": alert, "title": alert}}
        }
        return json.dumps(payload)

    def process(self, **kwargs):
        fcm_param = kwargs.get("fcm", {})
        collapse_key = fcm_param.get("collapse_key", None)
        ttl = fcm_param.get("ttl", None)
        alert = kwargs.get("alert", None)
        data = fcm_param.get("data", {})
        if "message" not in data:
            data["message"] = kwargs.get("alert", "")
        appdb = kwargs.get("appdb", None)
        return self.send(kwargs["token"], alert=alert, appdb=appdb)

    def send(self, token, alert=None, retries=5, appdb=None):
        """
        Send message to google gcm endpoint
        :param token: device token
        :param data: dict
        :param collapse_key: string
        :param ttl: int
        :param retries: int
        :param appdb: Database
        """
        if not token:
            raise FCMException("token is required")

        self.access_token_info = self.credentials.get_access_token()
        headers = {
            "Authorization": "Bearer %s" % self.access_token_info.access_token,
            "Content-Type": "application/json; UTF-8",
        }

        payload = self.build_request(token, alert)

        response = requests.post(self.endpoint, data=payload, headers=headers)

        if response.status_code == 400:
            _logger.info(response.json())
            jsonError = response.json()
            raise FCMException(jsonError["error"])
        elif response.status_code == 401:
            raise FCMException("There was an error authenticating the sender account.")
        elif response.status_code >= 500:
            raise FCMException("GCMClient server is temporarily unavailable .")
        return response

    def add_to_log(self, appdb, action, info=None, level="info"):
        log = {}
        log["action"] = strip_tags(action)
        log["info"] = strip_tags(info)
        log["level"] = strip_tags(level)
        log["created"] = int(time.time())
        if appdb is not None:
            appdb.logs.insert(log, safe=True)
