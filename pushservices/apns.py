#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import PushService
from util import json_decode, json_encode
import argparse
import datetime
import logging
import tornado
from hyper import HTTPConnection
import json
import jwt
import logging
import time

BASE_URL = "api.development.push.apple.com:443"
ALGORITHM = "ES256"


class ApnsException(Exception):
    def __init__(self, response_statuscode, error):
        self.response_statuscode = response_statuscode
        self.error = error


class ApnsClient(PushService):
    def __str__(self):
        return " APNsClient %s: %s" % (self.appname, self.instanceid)

    def __init__(self, **kwargs):
        self.auth_key = kwargs["auth_key"]
        self.bundle_id = kwargs["bundle_id"]
        self.key_id = kwargs["key_id"]
        self.team_id = kwargs["team_id"]
        self.appname = kwargs["appname"]
        self.instanceid = kwargs["instanceid"]
        self.http2 = HTTPConnection(BASE_URL)

    def build_headers(self):
        token = jwt.encode(
            {"iss": self.team_id, "iat": time.time()},
            self.auth_key,
            algorithm=ALGORITHM,
            headers={"alg": ALGORITHM, "kid": self.key_id},
        )

        return {
            "apns-expiration": "0",
            "apns-priority": "10",
            "apns-topic": self.bundle_id,
            "authorization": "bearer {0}".format(token.decode("ascii")),
        }

    def process(self, **kwargs):
        payload = kwargs.get("payload", {})
        extra = kwargs.get("extra", {})
        alert = kwargs.get("alert", None)
        apns = kwargs.get("apns", None)
        token = kwargs["token"]

        if alert is not None and not isinstance(alert, dict):
            alert = {"body": alert, "title": alert}

        payload_data = {"aps": {"alert": alert, **apns}}
        payload = json_encode(payload_data)

        logging.info(payload)

        PATH = "/3/device/{0}".format(token)
        headers = self.build_headers()

        self.http2.request("POST", PATH, payload, headers=headers)
        resp = self.http2.get_response()

        if resp.status >= 400:
            headers = resp.headers
            #  for k, v in headers.items():
            #      logging.error("%s: %s" % (k.decode("utf-8"), v.decode("utf-8")))
            body = resp.read().decode("utf-8")
            logging.error(body)
            raise ApnsException(400, body)
