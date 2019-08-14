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

from . import PushService
import requests
import logging
from tornado.options import options
import os.path
from tornado.httpclient import AsyncHTTPClient
from util import *

try:
    from urllib.parse import quote_plus
except:
    from urllib.parse import quote_plus

ENDPOINT = (
    "http://api.clickatell.com/http/sendmsg?user=%s&password=%s&api_id=%s&to=%s&text=%s"
)


class ClickatellClient(PushService):
    def __init__(self, masterdb, app, instanceid=0):
        self.app = app
        self.masterdb = masterdb

    def handle_response(self, response):
        # logging.info(response.body)
        pass

    def process(self, **kwargs):
        to = quote_plus(str(kwargs["token"]))
        alert = quote_plus(str(kwargs["alert"]))
        uri = ENDPOINT % (
            self.app["clickatellusername"],
            self.app["clickatellpassword"],
            self.app["clickatellappid"],
            to,
            alert,
        )
        http = AsyncHTTPClient()
        http.fetch(uri, self.handle_response, method="GET")
