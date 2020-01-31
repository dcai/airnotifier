#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import PushService
from util import json_encode
import logging
import hyper
import jwt
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
        self.last_token_refresh = 0
        self.token = None
        self.http2 = hyper.HTTPConnection(BASE_URL)

    def create_token(self):
        now = time.time()
        countdown = now - self.last_token_refresh
        if countdown > 60 * (60 - 10):
            jwt_payload = {"iss": self.team_id, "iat": time.time()}
            token = jwt.encode(
                jwt_payload,
                self.auth_key,
                algorithm=ALGORITHM,
                headers={"alg": ALGORITHM, "kid": self.key_id},
            )
            self.last_token_refresh = now
            self.token = token.decode("ascii")
        return self.token

    def build_headers(self):

        token = self.create_token()

        return {
            "apns-expiration": "0",
            "apns-priority": "10",
            "apns-topic": self.bundle_id,
            "mutable-content": "1",
            "authorization": "bearer {0}".format(token),
        }

    def process(self, **kwargs):
        alert = kwargs.get("alert", None)
        apns = kwargs.get("apns", {})
        token = kwargs["token"]

        if alert is not None and not isinstance(alert, dict):
            alert = {"body": alert, "title": alert}

        # data structure:
        # https://developer.apple.com/library/archive/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/PayloadKeyReference.html#//apple_ref/doc/uid/TP40008194-CH17-SW1
        payload_data = {"aps": {"alert": alert, **apns}}
        payload = json_encode(payload_data)
        self.payload = payload

        PATH = "/3/device/{0}".format(token)
        self.headers = self.build_headers()

        self.http2.request("POST", PATH, payload, headers=self.headers)
        resp = self.http2.get_response()

        if resp.status >= 400:
            #  headers = resp.headers
            #  for k, v in headers.items():
            #      logging.error("%s: %s" % (k.decode("utf-8"), v.decode("utf-8")))
            body = resp.read().decode("utf-8")
            logging.error(body)
            raise ApnsException(400, body)
