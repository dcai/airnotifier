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

from constants import VERSION
from hashlib import sha1
from os import path
from pymongo.errors import CollectionInvalid
from tornado.options import define, options
from util import *
import logging
import pymongo
import tornado.options


EMAIL = "admin@airnotifier"
DEFAULTPASSWORD = "admin"

define("masterdb", default="airnotifier", help="MongoDB DB to store information")
define("mongouri", default="mongodb://localhost:27017/", help="MongoDB host name")
EMAIL = "admin@airnotifier"
DEFAULTPASSWORD = "admin"

define("apns", default=(), help="APNs address and port")
define("pemdir", default="pemdir", help="Directory to store pems")
define(
    "passwordsalt", default="d2o0n1g2s0h3e1n1g", help="Being used to make password hash"
)


if __name__ == "__main__":
    if not path.exists("config.py"):
        raise Exception("Please create config.py before running install.py")

    tornado.options.parse_config_file("config.py")
    tornado.options.parse_command_line()
    mongodb = pymongo.MongoClient(options.mongouri)
    masterdb = mongodb[options.masterdb]

    collection_names = masterdb.collection_names()
    try:
        if not "applications" in collection_names:
            masterdb.create_collection("applications")
            logging.info("db.applications installed")
    except CollectionInvalid as ex:
        logging.info(("Failed to created applications collection", ex))
        pass

    try:
        if not "managers" in collection_names:
            masterdb.create_collection("managers")
            #  masterdb.managers.ensure_index("username", unique=True)
            masterdb.managers.ensure_index("email", unique=True)
            logging.info("db.managers installed")
            try:
                user = masterdb.managers.find_one({"email": EMAIL})
                if not user:
                    manager = {}
                    manager["email"] = EMAIL
                    manager["password"] = get_password(
                        DEFAULTPASSWORD, options.passwordsalt
                    )
                    manager["orgid"] = 0
                    masterdb["managers"].insert(manager)
                    logging.info(
                        "Admin user created, username: %s, password: %s"
                        % (EMAIL, DEFAULTPASSWORD)
                    )
            except Exception as ex:
                logging.error(("Failed to create admin user", ex))

    except CollectionInvalid:
        logging.info("Failed to created managers collection")
        pass

    try:
        if not "options" in collection_names:
            masterdb.create_collection("options")
            logging.info("db.options installed")
            try:
                version = masterdb["options"].find_one({"name": "version"})
                if not version:
                    option_ver = {}
                    option_ver["name"] = "version"
                    option_ver["value"] = VERSION
                    masterdb["options"].insert(option_ver)
                    logging.info(("Version number written: %s" % VERSION))
            except Exception:
                logging.error("Failed to write version number")
    except CollectionInvalid:
        logging.error("db.options installed")
