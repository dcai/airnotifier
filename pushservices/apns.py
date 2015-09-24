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
import binascii
import json
import logging
import struct
import time
from util import *

from tornado import ioloop, iostream

PAYLOAD_LENGTH = 256

apns = {
    'sandbox': ("gateway.sandbox.push.apple.com", 2195),
    'production': ("gateway.push.apple.com", 2195)
}

feedbackhost = {
    'sandbox': ("feedback.sandbox.push.apple.com", 2196),
    'production': ("feedback.push.apple.com", 2196)
}

class PayLoad(object):

    def __init__(self, alert=None, badge=None, sound=None, identifier=0, expiry=None, customparams=None):
        if expiry == None:
            self.expiry = long(time.time() + 60 * 60 * 24)
        else:
            self.expiry = expiry
        self.identifier = int(identifier)
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
            logging.error("Certificate file doesn't exist")
        if not keyexists:
            logging.error("Key file doesn't exist")
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
        logging.info("remote connected")

    def _on_feedback_service_read_close(self, data):
        self.shutdown()

    def _on_feedback_service_read_streaming(self, data):
        """ Feedback """
        pass

class APNClient(PushService):

    def is_online(self):
        return self.connected

    def __init__(self, env='sandbox', certfile="", keyfile="", appname="", instanceid=0):
        certexists = file_exists(certfile)
        keyexists = file_exists(keyfile)
        if not certexists or not keyexists:
            raise Exception("APNs certificate or key files do not exist")
        self.apns = apns[env]
        self.certfile = get_filepath(certfile)
        self.keyfile = get_filepath(keyfile)
        self.messages = deque()
        self.reconnect = True
	self.errors = None
        self.ioloop = ioloop.IOLoop.instance()

        self.appname = appname
        self.instanceid = instanceid

        self.connected = False

        self.connect()

    def build_request(self):
        pass

    def _on_remote_read_close(self, data):
        """ Close socket and reconnect """
        self.connected = False
        logging.warning('%s[%d] is offline %d' % (self.appname, self.instanceid, self.reconnect))

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
               10: "Shutdown",
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
            10      | Shutdown
            255     | None
        """
        self.connected = False
        if (len(data) == 0) and (self.reconnect == True):
            """
            if we get a 0 byte response and we're closing
            we should in theory just re-connect
            """
            logging.error('0 byte response recieved. Attempting re-connect')
            try:
                self.remote_stream.close()
                self.sock.close()
                self.connect()
            except Exception, ex:
                raise ex
            return
            """
            We return out of here because we don't want the "normal"
            reconnect to kick in.
            """

        if len(data) != 6:
            logging.error('response must be a 6-byte binary string.')
        else:
            (command, statuscode, identifier) = struct.unpack_from('!bbI', data, 0)
            logging.error('%s[%d] CMD: %s Status: %s ID: %s', self.appname, self.instanceid, command, status_table[statuscode], identifier)
            self.errors = "%s (ID: %s)" % (status_table[statuscode], identifier)

        try:
            self.remote_stream.close()
            self.sock.close()
            if self.reconnect:
                self.connect()
        except Exception, ex:
            raise ex

    def _on_remote_connected(self):
        self.connected = True
        """ Callback when connected to APNs """
        logging.info('APNs connection: %s[%d] is online' % (self.appname, self.instanceid))
        # Processing the messages queue
        while self._send_message():
            continue

    def connect(self):
        """ Setup socket """
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.remote_stream = iostream.SSLIOStream(self.sock, ssl_options=dict(certfile=self.certfile, keyfile=self.keyfile))
        self.remote_stream.connect(self.apns, self._on_remote_connected)
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
        self.send(token, pl)

    def send(self, deviceToken, payload):
        """ Pack payload and append to message queue """
        # logging.info("Notification through %s[%d]" % (self.appname, self.instanceid))
        json = payload.json()
        json_len = len(json)
        fmt = '!bIIH32sH%ds' % json_len
        # command = '\x00'
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
        # logging.info(deviceToken)
        m = struct.pack(fmt, command, identifier, expiry, tokenLength,
                        binascii.unhexlify(deviceToken),
                        json_len, json)
        self.messages.append(m)
        self.ioloop.add_callback(self._send_message)
        return True

    def getQueueLength(self):
        return len(self.messages)

    def hasError(self):
	return self.errors is not None

    def getError(self):
	temp = self.errors
	self.errors = None
	return temp

    def _send_message(self):
        if len(self.messages) and not self.remote_stream.closed():
            # First in first out
            msg = self.messages.popleft()
            try:
                self.remote_stream.write(msg)
            except Exception as ex:
                logging.exception(ex)
                # Push back to queue top
                self.messages.appendleft(msg)
                return False
            return True
        return False
