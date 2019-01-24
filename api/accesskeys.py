#!/usr/bin/python
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

try:
    from httplib import FORBIDDEN, OK
except:
    from http.client import FORBIDDEN, OK
from importlib import import_module

try:
    from hashlib import md5
except:
    import md5
import time
import uuid

from api import APIBaseHandler
from routes import route


@route(r"/api/v2/accesskeys[\/]?")
class AccessKeysV2Handler(APIBaseHandler):
    def initialize(self):
        self.accesskeyrequired = False
        self._time_start = time.time()

    def post(self):
        """Create access key
        """
        try:
            data = self.json_decode(self.request.body)

            # if not self.can('create_accesskey'):
            # self.send_response(FORBIDDEN, dict(error="No permission to create accesskey"))
            # return

            processor = data.get("processor", None)
            if not processor:
                data["permission"] = 0
            else:
                try:
                    proc = import_module("hooks." + processor)
                    data = proc.process_accesskey_payload(data)
                except Exception as ex:
                    self.send_response(FORBIDDEN, dict(error=str(ex)))
                    return

            key = {}
            key["contact"] = data.get("contact", "")
            key["description"] = data.get("description", "")
            key["created"] = int(time.time())
            key["permission"] = data["permission"]
            key["key"] = md5(str(uuid.uuid4())).hexdigest()
            self.db.keys.insert(key)
            self.send_response(OK, dict(accesskey=key["key"]))
        except Exception as ex:
            self.send_response(FORBIDDEN, dict(error=str(ex)))
