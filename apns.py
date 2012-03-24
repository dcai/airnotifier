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

import logging
import os
import binascii
import json
import struct
import datetime
import time

from collections import deque
from socket import ssl, socket, AF_INET, SOCK_STREAM
from ssl import wrap_socket
from tornado import ioloop
from tornado import iostream

class PayLoad(object):

    def __init__(self, alert=None, badge=None, sound=None, identifier=0, expiry=None):
        if expiry == None:
            self.expiry = long(time.time() + 60 * 60 * 24)
        else:
            self.expiry = expiry
        self.identifier = int(identifier)
        self.alert = alert
        self.badge = badge
        self.sound = sound

    def build_payload(self):
        item = {}
        item['alert'] = self.alert
        item['sound'] = self.sound
        item['badge'] = int(self.badge)

        payload = {'aps': item}
        return payload

    def json(self):
        jsontext = json.dumps(self.build_payload(), separators=(',', ':'))
        logging.info("PayLoad: %s", jsontext)
        return jsontext


class APNClient(object):

    def __init__(self, apns=(), certfile="", keyfile=""):
        self.apns = apns
        self.certfile = certfile
        self.keyfile = keyfile
        self.messages = deque()
        self.ioloop = ioloop.IOLoop.instance()
        self.connect()

    def build_request(self):
        pass

    def _on_remote_read_close(self, data):
        """ Close socket and reconnect """
        logging.warning('Connection closed')
        self.remote_stream.close()
        self.sock.close()
        self.connect()

    def _on_remote_read_streaming(self, data):
        """ Something bad happened """
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
              255: "None"}
        # The error response packet
        """
            Command
                | Status
                |   | Identifier
                |   |    |
                #   #   ####
        Bytes:  1   1    4

        Command always 8

        Status code | Desc
             0      | No errors
             1      | Processing error
             2      | Missing device token
             3      | Missing topic
             4      | Missing payload
             5      | Invalid token size
             6      | Invalid topic size
             7      | Invalid payload size
             8      | Invalid token
            255     | None
        """
        logging.info('read streaming')
        if len(data) != 6:
            logging.info('response must be a 6-byte binary string.')

        (command, statuscode, identifier) = struct.unpack_from('!bbI', data, 0)
        logging.info('CMD: %s Status: %s ID: %s', command, status_table[statuscode], identifier)

    def _on_remote_connected(self):
        """ Callback when connected to APNs """
        logging.info('Connected to APNs')
        # Processing the messages queue
        while self._send_message():
            continue

    def connect(self):
        """ Setup socket """
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.remote_stream = iostream.SSLIOStream(self.sock,
                ssl_options=dict(certfile=self.certfile, keyfile=self.keyfile)
                )
        self.remote_stream.connect(self.apns, self._on_remote_connected)
        self.remote_stream.read_until_close(self._on_remote_read_close,
                                            self._on_remote_read_streaming)

    def send(self, deviceToken, payload):
        """ Pack payload and append to message queue """
        json = payload.json()
        json_len = len(json)
        fmt = '!bIIH32sH%ds' % json_len
        #command = '\x00'
        # enhanced notification has command 1
        command = 1
        """
        Simple notification format

              Command
                 | Id (will be returned if error)
                 |  |  Expiry
                 |  |    |   Token length
                 |  |    |    |   Token
                 |  |    |    |     |  Payload length
                 |  |    |    |     |     |    Payload
                 |  |    |    |     |     |       |
                 # #### ####  ## ######## ## ###########
        bytes    1  4    4    2     32    2      34
                              |           |
                           Big endian     |
                                      Big endian

        """
        identifier = payload.identifier
        # One day
        expiry = payload.expiry
        tokenLength = 32
        logging.info("token length %s", len(deviceToken))
        m = struct.pack(fmt, command, identifier, expiry, tokenLength,
                        binascii.unhexlify(deviceToken),
                        json_len, json)
        self.messages.append(m)
        self.ioloop.add_callback(self._send_message)
        return True

    def _send_message(self):
        if len(self.messages) and not self.remote_stream.closed():
            # First in first out
            msg = self.messages.popleft()
            # TODO: Log this action
            try:
                self.remote_stream.write(msg)
            except Exception, ex:
                logging.exception(ex)
                # Push back to queue
                self.messages.appendleft(msg)
                return False
            return True
        return False


if __name__ == '__main__':
    pl = PayLoad(alert='Hello world', sound='default', badge=1)
    apn = APNClient()
    apn.send('9116fc350fbcb47a0ed078e214b7f13a9e9cb02105d16d76381c700e1da6c2be'
                     , pl.json())
    ioloop.IOLoop.instance().start()
