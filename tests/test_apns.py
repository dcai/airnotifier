from pushservices.apns import ApnsClient
import unittest
import logging
import sys
from unittest.mock import MagicMock, patch
from util import json_decode


def mocked_http2(*args, **kwargs):
    class Response:
        def __init__(self):
            self.status = 200

        def read(self):
            return b"{}"

    class HTTP2:
        def request(self, method, path, payload, **kwargs):
            pass

        def get_response(self):
            return Response()

    return HTTP2()


def mocked_jwt_encode(*args, **kwargs):
    class Token:
        def decode(self, string):
            return "encode_jwt"

    return Token()


class TestAPNS(unittest.TestCase):
    @patch("jwt.encode", side_effect=mocked_jwt_encode)
    @patch("hyper.HTTPConnection", side_effect=mocked_http2)
    def test_apns(self, jwt, req):
        self.maxDiff = None
        kwargs = {
            "project_id": "xxx",
            "auth_key": "iiii",
            "bundle_id": "com.airnotifier",
            "key_id": "xxxx",
            "team_id": "xxxx",
            "appname": "",
            "instanceid": "",
        }
        apns = ApnsClient(**kwargs)
        apns_default = {"badge": None, "sound": "default", "push_type": "alert"}
        apns.process(
            token="aaa", alert="alert", apns={**apns_default, **{"badge": 12}},
        )
        self.assertDictEqual(
            apns.headers,
            {
                "apns-expiration": "0",
                "apns-priority": "10",
                "apns-push-type": "alert",
                "apns-topic": "com.airnotifier",
                "authorization": "bearer encode_jwt",
                "mutable-content": "1",
            },
        )
        self.assertEqual(
            apns.payload,
            '{"aps": {"alert": {"body": "alert", "title": "alert"}, "badge": 12, "sound": "default"}}',
        )
        apns.process(
            token="aaa",
            alert="alert",
            apns={**apns_default, **{"badge": 12, "push_type": "background"}},
        )
        self.assertDictEqual(
            apns.headers,
            {
                "apns-expiration": "0",
                "apns-priority": "10",
                "apns-push-type": "background",
                "apns-topic": "com.airnotifier",
                "authorization": "bearer encode_jwt",
                "mutable-content": "1",
            },
        )


if __name__ == "__main__":
    unittest.main()
