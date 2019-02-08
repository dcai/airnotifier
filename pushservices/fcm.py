#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import requests
from . import PushService
import json
import time
from util import strip_tags
import logging
from oauth2client.service_account import ServiceAccountCredentials

BASE_URL = "https://fcm.googleapis.com"
SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]
_logger = logging.getLogger("fcm")


class FCMException(Exception):
    def __init__(self, error):
        self.error = error


class FCMClient(PushService):
    def __str__(self):
        return "endpoint: %s" % (self.endpoint)

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

    def build_request(self, token, alert, android=None, data=None, extra=None):
        isDict = isinstance(alert, dict)
        body = alert
        title = alert
        if isDict:
            body = alert["body"]
            title = alert["title"]

        data["extra"] = extra

        # data strcuture: https://firebase.google.com/docs/reference/fcm/rest/v1/projects.messages
        payload = {
            "message": {
                "token": token,
                "notification": {"body": body, "title": title},
                "android": android,
                "data": data,
            }
        }
        return json.dumps(payload)

    def process(self, **kwargs):
        fcm_param = kwargs.get("fcm", {})
        extra = kwargs.get("extra", {})
        alert = kwargs.get("alert", None)
        android = fcm_param.get("android", {})
        data = fcm_param.get("data", {})
        appdb = kwargs.get("appdb", None)
        return self.send(
            kwargs["token"],
            alert=alert,
            appdb=appdb,
            android=android,
            extra=extra,
            data=data,
        )

    def send(self, token, alert=None, data=None, appdb=None, android=None, extra=None):
        """
        Send message to google gcm endpoint
        :param token: device token
        :param data: dict
        :param appdb: Database
        """
        if not token:
            raise FCMException("token is required")

        self.access_token_info = self.credentials.get_access_token()
        headers = {
            "Authorization": "Bearer %s" % self.access_token_info.access_token,
            "Content-Type": "application/json; UTF-8",
        }

        payload = self.build_request(token, alert, android, data, extra)
        response = requests.post(self.endpoint, data=payload, headers=headers)

        if response.status_code >= 400:
            jsonError = response.json()
            _logger.info(jsonError)
            raise FCMException(jsonError["error"])
        return response

    def add_to_log(self, appdb, action, info=None, level="info"):
        log = {}
        log["action"] = strip_tags(action)
        log["info"] = strip_tags(info)
        log["level"] = strip_tags(level)
        log["created"] = int(time.time())
        if appdb is not None:
            appdb.logs.insert(log)
