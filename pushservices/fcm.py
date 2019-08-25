#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import requests
from util import json_decode, json_encode
from . import PushService
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
        jsonData = json_decode(jsonkey)
        self.credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            jsonData, SCOPES
        )
        self.endpoint = "%s/v1/projects/%s/messages:send" % (BASE_URL, self.project_id)

    def format_values(self, data=None):
        if not isinstance(data, dict):
            return data

        # Try to convert all fields to string.
        formatted = {}

        for (k, v) in data.items():
            if isinstance(v, bool):
                formatted[k] = "1" if v else "0"

            elif isinstance(v, dict):
                try:
                    formatted[k] = json_encode(self.format_values(v))
                except:
                    _logger.error("Error treating field " + k)

            elif v is not None:
                formatted[k] = str(v)

        return formatted

    def build_request(self, token, alert, **kwargs):
        if alert is not None and not isinstance(alert, dict):
            alert = {"body": alert, "title": alert}

        fcm_param = kwargs.get("payload", {})
        android = fcm_param.get("android", {})
        apns = fcm_param.get("apns", {})
        webpush = fcm_param.get("webpush", {})
        data = fcm_param.get("data", {})

        # data structure: https://firebase.google.com/docs/reference/fcm/rest/v1/projects.messages
        payload = {"message": {"token": token}}

        if alert:
            payload["message"]["notification"] = self.format_values(alert)

        if data:
            payload["message"]["data"] = self.format_values(data)

        if android:
            payload["message"]["android"] = android

        if webpush:
            payload["message"]["webpush"] = webpush

        if apns:
            payload["message"]["apns"] = apns

        text = json_encode(payload)
        return text

    def process(self, **kwargs):

        payload = kwargs.get("payload", {})
        extra = kwargs.get("extra", {})
        alert = kwargs.get("alert", None)
        appdb = kwargs.get("appdb", None)
        token = kwargs["token"]

        if not token:
            raise FCMException("token is required")

        access_token_info = self.credentials.get_access_token()
        headers = {
            "Authorization": "Bearer %s" % access_token_info.access_token,
            "Content-Type": "application/json; UTF-8",
        }

        data = self.build_request(token, alert, extra=extra, payload=payload)
        response = requests.post(self.endpoint, data=data, headers=headers)

        if response.status_code >= 400:
            jsonError = response.json()
            _logger.error(jsonError)
            raise FCMException(jsonError["error"])
        return response
