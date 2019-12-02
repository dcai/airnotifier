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
from util import strip_tags
import json
import logging
import requests
import time
from util import json_decode, json_encode

GCM_ENDPOINT = "https://fcm.googleapis.com/fcm/send"


class GCMException(Exception):
    pass


class GCMNotRegisteredException(GCMException):
    def __init__(self, regids):
        Exception.__init__(self, "Not Registered")
        self.regids = regids


class GCMInvalidRegistrationException(GCMException):
    def __init__(self, regids):
        Exception.__init__(self, "Invalid Registration")
        self.regids = regids


class GCMUpdateRegIDsException(GCMException):
    def __init__(self, canonical_ids):
        Exception.__init__(self, "Canonical ids")
        self.canonical_ids = canonical_ids


class GCMClient(PushService):
    def __init__(
        self, projectnumber, apikey, appname, instanceid=0, endpoint=GCM_ENDPOINT
    ):
        self.projectnumber = projectnumber
        self.apikey = apikey
        self.appname = appname
        self.instanceid = instanceid
        self.endpoint = endpoint

    def build_request(self, regids, data, collapse_key, ttl):
        payload = {"registration_ids": regids}
        if data:
            payload["data"] = data

        if ttl >= 0:
            payload["time_to_live"] = ttl

        if collapse_key:
            payload["collapse_key"] = collapse_key

        return json_encode(payload)

    def reverse_response_info(self, key, ids, results):
        zipped = list(zip(ids, results))
        # Get items having error key
        filtered = [x for x in zipped if key in x[1]]
        # Expose error value
        exposed = [(s[0], s[1][key]) for s in filtered]
        errors = {}
        for k, v in exposed:
            if v not in errors:
                errors[v] = []
            errors[v].append(k)
        return errors

    def process(self, **kwargs):
        gcmparam = kwargs.get("gcm", {})
        collapse_key = gcmparam.get("collapse_key", None)
        ttl = gcmparam.get("ttl", None)
        alert = kwargs.get("alert", None)
        data = gcmparam.get("data", {})
        if "message" not in data:
            data["message"] = kwargs.get("alert", "")
        appdb = kwargs.get("appdb", None)
        return self.send(
            kwargs["token"], data=data, collapse_key=collapse_key, ttl=ttl, appdb=appdb
        )

    def send(
        self, regids, data=None, collapse_key=None, ttl=None, retries=5, appdb=None
    ):
        """
        Send message to google gcm endpoint
        :param regids: list
        :param data: dict
        :param collapse_key: string
        :param ttl: int
        :param retries: int
        :param appdb: Database
        """
        if not regids:
            raise GCMException("Registration IDs cannot be empty")

        payload = self.build_request(regids, data, collapse_key, ttl)
        headers = {
            "content-type": "application/json",
            "Authorization": "key=%s" % self.apikey,
        }
        response = requests.post(self.endpoint, data=payload, headers=headers)

        if response.status_code == 400:
            raise GCMException(
                "Request could not be parsed as JSON, or it contained invalid fields."
            )
        elif response.status_code == 401:
            raise GCMException("There was an error authenticating the sender account.")
        elif response.status_code >= 500:
            raise GCMException("GCMClient server is temporarily unavailable .")

        responsedata = response.json()
        if responsedata.get("canonical_ids", 0) != 0:
            # means we need to take a look at results, looking for registration_id key
            responsedata["canonical_ids"] = self.reverse_response_info(
                "registration_id", regids, responsedata["results"]
            )

        # Handling errors
        if responsedata.get("failure", 0) != 0:
            # means we need to take a look at results, looking for error key
            errors = self.reverse_response_info(
                "error", regids, responsedata["results"]
            )
            for errorkey, packed_rregisteration_ids in list(errors.items()):
                # Check for errors and act accordingly
                if errorkey == "NotRegistered":
                    # Should remove the registration ID from your server database
                    # because the application was uninstalled from the device or
                    # it does not have a broadcast receiver configured to receive
                    if appdb is not None:
                        appdb.tokens.delete_many(
                            {"token": {"$in": packed_rregisteration_ids}}
                        )
                        self.add_to_log(
                            appdb,
                            "GCM",
                            "Cleaned unregistered tokens: "
                            + ", ".join(packed_rregisteration_ids),
                        )
                    else:
                        raise GCMNotRegisteredException(packed_rregisteration_ids)
                elif errorkey == "InvalidRegistration":
                    # You should remove the registration ID from your server
                    # database because the application was uninstalled from the device or it does not have a broadcast receiver configured to receive
                    if appdb is not None:
                        appdb.tokens.delete_many(
                            {"token": {"$in": packed_rregisteration_ids}}
                        )
                        self.add_to_log(
                            appdb,
                            "GCM",
                            "Cleaned invalid tokens: "
                            + ", ".join(packed_rregisteration_ids),
                        )
                    else:
                        raise GCMInvalidRegistrationException(packed_rregisteration_ids)
                elif errorkey == "MismatchSenderId":
                    """
                    A registration ID is tied to a certain group of senders. When an application registers for GCMClient usage,
                    it must specify which senders are allowed to send messages. Make sure you're using one of those when
                    trying to send messages to the device. If you switch to a different sender, the existing registration
                    IDs won't work.
                    """
                    raise GCMException("Mismatch sender Id")
                elif errorkey == "MissingRegistration":
                    """
                    Check that the request contains a registration ID (either in the registration_id parameter in a
                    plain text message, or in the registration_ids field in JSON).
                    """
                    raise GCMException("Missing registration")
                elif errorkey == "MessageTooBig":
                    raise GCMException("Message too big")
                elif errorkey == "InvalidDataKey":
                    raise GCMException("Invalid data key")
                elif errorkey == "InvalidTtl":
                    raise GCMException("Invalid Ttl")
                elif errorkey == "InvalidPackageName":
                    raise GCMException("Invalid package name")
                raise GCMException("Unknown error, contact admin")

        return response

    def add_to_log(self, appdb, action, info=None, level="info"):
        log = {}
        log["action"] = strip_tags(action)
        log["info"] = strip_tags(info)
        log["level"] = strip_tags(level)
        log["created"] = int(time.time())
        if appdb is not None:
            appdb.logs.insert(log)
