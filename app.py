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


from container import Container
from dao import Dao
from pushservices.bootstrap import init_messaging_agents
from sentry_sdk.integrations.tornado import TornadoIntegration
from tornado.options import define, options
from web import WebApplication
import logging
import logging.config
import os
import pymongo
import sentry_sdk


define("appprefix", default="", help="DB name prefix")
define("collectionprefix", default="obj_", help="Collection name prefix")
define("cookiesecret", default="airnotifiercookiesecret", help="Cookie secret")
define("dbprefix", default="app_", help="DB name prefix")
define("debug", default=False, help="Debug mode")
define("https", default=False, help="Enable HTTPS")
define("httpscertfile", default="", help="HTTPS cert file")
define("httpskeyfile", default="", help="HTTPS key file")
define("masterdb", default="airnotifier", help="MongoDB DB to store information")
define("mongouri", default="mongodb://localhost:27017/", help="MongoDB host name")
define(
    "passwordsalt", default="d2o0n1g2s0h3e1n1g", help="Being used to make password hash"
)
define("pemdir", default="pemdir", help="Directory to store pems")
define("port", default=8801, help="Application server listen port", type=int)
define("sentrydsn", default="", help="sentry dsn")


if __name__ == "__main__":
    loggingconfigfile = "logging.ini"

    if os.path.isfile(loggingconfigfile):
        logging.config.fileConfig(loggingconfigfile)

    options.parse_config_file("config.py")
    options.parse_command_line()

    if options.sentrydsn:
        sentry_sdk.init(dsn=options.sentrydsn, integrations=[TornadoIntegration()])
    else:
        logging.warn("Sentry dsn is not set")

    mongodb = None
    while not mongodb:
        try:
            mongodb = pymongo.MongoClient(options.mongouri)
        except:
            logging.error("Cannot not connect to MongoDB")

    masterdb = mongodb[options.masterdb]
    services = init_messaging_agents(masterdb)

    SYSTEM_DATA = (
        ("mongodburi", options.mongouri, None),
        ("mongodbconn", mongodb, None),
        ("services", services, None),
        ("serveroptions", options, None),
        ("dao", Dao, ("mongodbconn", "serveroptions")),
    )

    container = Container(SYSTEM_DATA)

    WebApplication(container).main()
