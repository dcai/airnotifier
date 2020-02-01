from api.push import PushHandler
from tornado.testing import AsyncTestCase, AsyncHTTPTestCase
from container import Container
import tornado.httpserver
import tornado.httpclient
import tornado.ioloop
import tornado.web
import unittest
from tornado.options import define, options

define("appprefix", default="")


class HelloHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")


class CollectionAPI:
    def __init__(self):
        pass

    def find_one(self, xxx):
        return {"permission": 31}

    def insert(self, xxx):
        pass


class MockMongo:
    def __init__(self):
        self.keys = CollectionAPI()
        self.logs = CollectionAPI()


class MockFcm:
    def __init__(self):
        pass

    async def process(self, **kwargs):
        pass


services = {"fcm": {"myapp": [MockFcm()]}}


class WebApplication(tornado.web.Application):
    def __init__(self, handlers, container):
        self.container = container
        self.services = services
        self.mongodb = {"myapp": MockMongo()}
        tornado.web.Application.__init__(self, handlers)


class Dao:
    def __init__(self, mongodb, appoptions):
        self.mongodb = mongodb
        self.masterdb = None
        self.options = appoptions

    def set_current_app(self, name):
        pass

    def get_version(self):
        return "2.0.0"

    def find_app_by_name(self, name):
        return {"name": name, "shortname": name}

    def update_app_by_name(self, name):
        pass

    def find_token(self, token):
        return {"token": token}

    def add_token(self):
        pass


def make_app():
    data = (
        ("mongodburi", ".........", None),
        ("mongodbconn", "....", None),
        ("services", "...", None),
        ("serveroptions", "xxxx", None),
        ("dao", Dao, ("mongodbconn", "serveroptions")),
    )
    container = Container(data)
    return WebApplication(
        [(r"/push", PushHandler), (r"/hello", HelloHandler)], container
    )


headers = {
    "X-AN-APP-NAME": "myapp",
    "X-AN-APP-KEY": "xxxx",
}


class TestHelloApp(AsyncHTTPTestCase):
    def get_app(self):
        return make_app()

    def test_hello(self):
        response = self.fetch("/hello")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body.decode("utf-8"), "Hello, world")

    def test_push(self):
        body = '{"token":"xx", "device":"android-fcm", "alert":"aaa"}'
        response = self.fetch("/push", method="POST", body=body, headers=headers)
        self.assertEqual(response.code, 202)
        #  self.assertEqual(response.body.decode("utf-8"), "Hello, world")


if __name__ == "__main__":
    unittest.main()
