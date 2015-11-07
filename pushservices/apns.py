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

from . import PushService
from collections import deque
from socket import socket, AF_INET, SOCK_STREAM
import json
import logging
import struct
import time
import os
from util import *
from binascii import hexlify, unhexlify
from tornado import ioloop, iostream
import string
import random

_logger = logging.getLogger(__name__)

PAYLOAD_LENGTH = 256

SIMPLE_NOTIFICATION_COMMAND = 0
ENHANCED_NOTIFICATION_COMMAND = 1
TOKEN_LENGTH = 32

apns = {
    'sandbox': ("gateway.sandbox.push.apple.com", 2195),
    'production': ("gateway.push.apple.com", 2195)
}

feedbackhost = {
    'sandbox': ("feedback.sandbox.push.apple.com", 2196),
    'production': ("feedback.push.apple.com", 2196)
}
def id_generator(size=4, chars=string.ascii_letters + string.digits):
    """  string.ascii_letters + string.digits + string.punctuation """
    return ''.join(random.choice(chars) for _ in range(size))

class PayLoad(object):
    def __init__(self, alert=None, badge=None, sound=None, identifier=0, expiry=None, customparams=None):
        if expiry == None:
            self.expiry = long(time.time() + 60 * 60 * 24)
        else:
            self.expiry = expiry
        if not identifier:
            self.identifier = id_generator(4)
        self.alert = alert
        self.badge = badge
        self.sound = sound
        self.customparams = customparams

    def build_payload(self):
        alertlength = PAYLOAD_LENGTH
        # remove {"aps":{"alert":""}}
        alertlength = alertlength - 20
        item = {}
        if self.sound is not None:
            # remove sound field ,'sound':""
            alertlength = alertlength - 11 - len(self.sound)
            item['sound'] = self.sound
        if self.badge:
            # remove sound field ,'badge':""
            alertlength = alertlength - 11 - len(str(self.badge))
            item['badge'] = int(self.badge)

        if type(self.alert) is dict:
            item['alert'] = self.alert
        else:
            if len(self.alert) > alertlength:
                alertlength = alertlength - 3
                item['alert'] = self.alert[:alertlength] + '...'
            else:
                item['alert'] = self.alert

        payload = {'aps': item}
        if self.customparams != None:
            payload = dict(payload.items() + self.customparams.items())
        return payload

    def json(self):
        jsontext = json.dumps(self.build_payload(), separators=(',', ':'))
        return jsontext

class APNFeedback(object):
    def __init__(self, env="sandbox", certfile="", keyfile="", appname=""):
        certexists = file_exists(certfile)
        keyexists = file_exists(keyfile)
        if not certexists:
            _logger.error("Certificate file doesn't exist")
        if not keyexists:
            _logger.error("Key file doesn't exist")
        if not certexists and not keyexists:
            raise Exception("Cert or Key not exist")
        self.host = feedbackhost[env]
        self.certfile = get_filepath(certfile)
        self.keyfile = get_filepath(keyfile)
        self.ioloop = ioloop.IOLoop.instance()
        self.appname = appname
        self.connect()

    def connect(self):
        """ Setup socket """
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.remote_stream = iostream.SSLIOStream(self.sock, ssl_options=dict(certfile=self.certfile, keyfile=self.keyfile))
        self.remote_stream.connect(self.host, self._on_feedback_service_connected)
        self.remote_stream.read_until_close(self._on_feedback_service_read_close,
                                            self._on_feedback_service_read_streaming)

    def shutdown(self):
        """Shutdown this connection"""
        self.remote_stream.close()
        self.sock.close()

    def _on_feedback_service_connected(self):
        _logger.info("APNs connected")

    def _on_feedback_service_read_close(self, data):
        self.shutdown()

    def _on_feedback_service_read_streaming(self, data):
        """ Feedback """
        fmt = (
            '!'
            'I'   # expiry
            'H'   # token length
            '32s' # token
        )
        if len(data):
            _logger.info(data)
        else:
            _logger.info("no data")


class APNClient(PushService):

    def is_online(self):
        return self.connected

    def __init__(self, env='sandbox', certfile="", keyfile="", appname="", instanceid=0):
        self.apnsendpoint = apns[env]

        self.appname = appname
        self.instanceid = instanceid
        self.messages = deque()

        certexists = file_exists(certfile)
        keyexists = file_exists(keyfile)
        if not certexists or not keyexists:
            raise Exception("APNs certificate or key files do not exist")

        self.certfile = get_filepath(certfile)
        self.keyfile = get_filepath(keyfile)
        self.sock = None
        self.remote_stream = None
        self.connected = False
        self.reconnect = True
        self.ioloop = ioloop.IOLoop.instance()
        self.errors = None

        self.connect()

    def _on_remote_connected(self):
        self.connected = True
        """ Callback when connected to APNs """
        _logger.info('APNs connection: %s[%d] is online' % (self.appname, self.instanceid))
        # Processing the messages queue
        while self._write_to_remote_stream_from_queue():
            continue

    def _on_remote_read_close(self, data):
        """ Close socket and reconnect """
        self.connected = False
        _logger.warning('%s[%d] is offline. Reconnected?: %d' % (self.appname, self.instanceid, self.reconnect))
        """
            Command
                | Status
                |   | Identifier
                |   |    |
                #   #   ####
        Bytes:  1   1    4

        Command always 8
        """
        status_table = {
                0: "No erros",
                1: "Processing error",
                2: "Mssing device token",
                3: "Missing topic",
                4: "Missing payload",
                5: "Invalid token size",
                6: "Invalid topic size",
                7: "Invalid payload size",
                8: "Invalid token",
               10: "Shutdown",
              255: "None"}
        # The error response packet
        self.connected = False
        if (len(data) == 0) and (self.reconnect == True):
            """
            if we get a 0 byte response and we're closing
            we should in theory just re-connect
            """
            _logger.error('0 byte recieved.')
            try:
                self.remote_stream.close()
                self.sock.close()
                _logger.error('Attempting re-connect...')
                self.connect()
            except Exception as ex:
                raise ex
            return
            """
            We return out of here because we don't want the "normal"
            reconnect to kick in.
            """

        if len(data) != 6:
            _logger.error('response must be a 6-byte binary string.')
        else:
            error_format = (
                '!'  # network big-endian
                'b'  # command, should be 8
                'b'  # status
                '4s'  # identifier
            )
            (command, statuscode, identifier) = struct.unpack_from(error_format, data, 0)
            # command should be 8
            _logger.error('%s[%d] Status: %s MSGID: #%s', self.appname,
                    self.instanceid, status_table[statuscode], identifier)

            self.errors = "%s (ID: %s)" % (status_table[statuscode], identifier)

        try:
            self.remote_stream.close()
            self.sock.close()
            if self.reconnect:
                self.connect()
        except Exception as ex:
            raise ex

    def connect(self):
        """ Setup socket """
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.remote_stream = iostream.SSLIOStream(self.sock, ssl_options=dict(certfile=self.certfile, keyfile=self.keyfile))
        self.remote_stream.connect(self.apnsendpoint, self._on_remote_connected)
        self.remote_stream.read_until_close(self._on_remote_read_close)

    def shutdown(self):
        """Shutdown this connection"""
        self.reconnect = False
        self.remote_stream.close()
        self.sock.close()

    def disconnect(self):
        """Disconnect"""
        self.remote_stream.close()
        self.sock.close()

    def process(self, **kwargs):
        token = kwargs['token']
        apnsparams = kwargs['apns']
        sound = apnsparams.get('sound', None)
        badge = apnsparams.get('badge', None)
        customparams = apnsparams.get('custom', None)
        pl = PayLoad(alert=kwargs['alert'], sound=sound, badge=badge, identifier=0, expiry=None, customparams=customparams)
        self._append_to_queue(token, pl)

    def sendbulk(self, deviceToken, payload):
        """ TODO """
        msghead = '!bI'
        msghead = (
            '!'  # network big-endian
            'b'  # command -> 2
            'I'  # Frame length
        )
        itemheadfmt = (
            'b'  # item ID
            'I'  # item length
        )
        itembodyfmt = (
            '32s' # token
            '%ds' # payload
            'I'   # notification identifier
            'I'   # expiry date
            'b'   # priority
        ) % (payload_length, notification_id)

    def getQueueLength(self):
        return len(self.messages)

    def hasError(self):
        return self.errors is not None

    def getError(self):
        temp = self.errors
        self.errors = None
        return temp

    def _append_to_queue(self, deviceToken, payload):
        """ Pack payload and append to message queue """
        # _logger.info("Notification through %s[%d]" % (self.appname, self.instanceid))
        json = payload.json()
        _logger.info(json)
        json_len = len(json)
        fmt = (
            '!'   # network big-endian
            'b'   # command
            '4s'  # identifier
            'I'   # expiry
            'H'   # token length
            '32s' # token
            'H'   # payload length
            '%ds' # payload
        ) % json_len
        """
        Legacy APNs format

        Enhanced Notification Format
        https://developer.apple.com/library/ios/documentation/NetworkingInternet/Conceptual/RemoteNotificationsPG/Chapters/LegacyFormat.html

              Command
                 |
                 | Id (will be returned if error)
                 |  |
                 |  |  Expiry
                 |  |    |
                 |  |    |   Token length
                 |  |    |    |
                 |  |    |    |   Token
                 |  |    |    |     |
                 |  |    |    |     |  PL length
                 |  |    |    |     |     |
                 |  |    |    |     |     |    Payload
                 |  |    |    |     |     |       |
                 # #### ####  ## ######## ## ###########
        bytes    1  4    4    2     32    2      34
                              |           |
                           Big endian     |
                                          |
                                      Big endian

        """
        identifier = payload.identifier
        # One day
        expiry = payload.expiry
        _logger.info("MSGID #%s => %s" % (identifier, deviceToken))
        frame = struct.pack(fmt, ENHANCED_NOTIFICATION_COMMAND, identifier, expiry,
                TOKEN_LENGTH, unhexlify(deviceToken), json_len, json)
        self.messages.append(frame)
        # Calls the given callback on the next I/O loop iteration.
        self.ioloop.add_callback(self._write_to_remote_stream_from_queue)
        return True

    def _write_to_remote_stream_from_queue(self):
        if len(self.messages) and not self.remote_stream.closed():
            # First in first out
            msg = self.messages.popleft()
            try:
                self.remote_stream.write(msg)
            except Exception as ex:
                _logger.exception(ex)
                # Push back to queue top
                self.messages.appendleft(msg)
                return False
            return True
        return False
