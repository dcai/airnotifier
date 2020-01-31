from pushservices.fcm import FCMClient
import unittest
import sys
from unittest.mock import MagicMock, patch
from util import json_decode


def mocked_tornado_http(*args, **kwargs):
    class HTTP:
        async def fetch(self, url, **kwargs):
            body = kwargs["body"]
            return body

    return HTTP()


def mocked_oauth(*args, **kwargs):
    class Client:
        def get_access_token(self):
            return ("access_token", 11111)

    return Client()


class TestFCM(unittest.IsolatedAsyncioTestCase):
    @patch("tornado.httpclient.AsyncHTTPClient", side_effect=mocked_tornado_http)
    @patch(
        "oauth2client.service_account.ServiceAccountCredentials.from_json_keyfile_dict",
        side_effect=mocked_oauth,
    )
    async def test_fcm(self, req, oauth):
        self.maxDiff = None
        kwargs = {"project_id": "xxx", "jsonkey": "{}", "appname": "", "instanceid": ""}
        fcm = FCMClient(**kwargs)
        accesstoken, e = fcm.oauth_client.get_access_token()
        self.assertEqual(accesstoken, "access_token")
        response = await fcm.process(
            token="aaa",
            alert="alert",
            fcm={
                "android": {"droid": 1},
                "apns": {"apple": 2},
                "webpush": {},
                "data": {},
            },
        )
        self.assertDictEqual(
            json_decode(response),
            {
                "message": {
                    "token": "aaa",
                    "notification": {"body": "alert", "title": "alert"},
                    "android": {"droid": 1},
                    "apns": {"apple": 2},
                }
            },
        )


if __name__ == "__main__":
    unittest.main()
