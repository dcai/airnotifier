from typing import Dict
import logging


class Dao:
    def __init__(self, mongodb, options):
        self.mongodb = mongodb
        self.masterdb = mongodb[options.masterdb]
        self.options = options

    def set_current_app(self, name):
        dbname = self.options.appprefix + name
        self.db = self.mongodb[dbname]

    def get_version(self):
        return "2.0.0"

    def find_app_by_name(self, name):
        return self.masterdb.applications.find_one({"shortname": name})

    def update_app_by_name(self, name: str, app: Dict[str, str]):
        self.masterdb.applications.update({"shortname": name}, app)

    def find_token(self, token):
        logging.info("find token: %s" % token)
        return self.db.tokens.find_one({"token": token})

    def add_token(self, token: Dict[str, str]):
        return self.db.tokens.insert(token)
