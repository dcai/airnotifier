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
    from httplib import BAD_REQUEST, FORBIDDEN, \
        INTERNAL_SERVER_ERROR, ACCEPTED
except:
    from http.client import BAD_REQUEST, FORBIDDEN, \
        INTERNAL_SERVER_ERROR, ACCEPTED
from routes import route
from api import APIBaseHandler, EntityBuilder
import random
import time
from importlib import import_module
from constants import DEVICE_TYPE_IOS, DEVICE_TYPE_ANDROID, DEVICE_TYPE_WNS, \
    DEVICE_TYPE_MPNS, DEVICE_TYPE_SMS
from pushservices.gcm import GCMUpdateRegIDsException, \
    GCMInvalidRegistrationException, GCMNotRegisteredException, GCMException
import logging

_logger = logging.getLogger(__name__)

@route(r"/api/v2/push[\/]?")
class PushHandler(APIBaseHandler):
    def validate_data(self, data):
        data.setdefault('channel', 'default')
        data.setdefault('sound', None)
        data.setdefault('badge', None)
        data.setdefault('extra', {})
        return data

    def get_apns_conn(self):
        if not self.apnsconnections.has_key(self.app['shortname']):
            self.send_response(INTERNAL_SERVER_ERROR, dict(error="APNs is offline"))
            return
        count = len(self.apnsconnections[self.app['shortname']])
        # Find an APNS instance
        random.seed(time.time())
        instanceid = random.randint(0, count - 1)
        return self.apnsconnections[self.app['shortname']][instanceid]

    def post(self):
        try:
            """ Send notifications """
            if not self.can("send_notification"):
                self.send_response(FORBIDDEN, dict(error="No permission to send notification"))
                return

            # if request body is json entity
            data = self.json_decode(self.request.body)

            data = self.validate_data(data)

            # Hook
            if 'extra' in data:
                if 'processor' in data['extra']:
                    try:
                        proc = import_module('hooks.' + data['extra']['processor'])
                        data = proc.process_pushnotification_payload(data)
                    except Exception as ex:
                        self.send_response(BAD_REQUEST, dict(error=str(ex)))

            if not self.token:
                self.token = data.get('token', None)

            # application specific data
            extra = data.get('extra', {})

            device = data.get('device', DEVICE_TYPE_IOS).lower()
            channel = data.get('channel', 'default')
            token = self.db.tokens.find_one({'token': self.token})

            if not token:
                token = EntityBuilder.build_token(self.token, device, self.appname, channel)
                if not self.can("create_token"):
                    self.send_response(BAD_REQUEST, dict(error="Unknow token and you have no permission to create"))
                    return
                try:
                    # TODO check permission to insert
                    self.db.tokens.insert(token, safe=True)
                except Exception as ex:
                    self.send_response(INTERNAL_SERVER_ERROR, dict(error=str(ex)))

            if device == DEVICE_TYPE_SMS:
                data.setdefault('sms', {})
                data['sms'].setdefault('to', data.get('token', ''))
                data['sms'].setdefault('message', data.get('message', ''))
                sms = self.smsconnections[self.app['shortname']][0]
                sms.process(token=data['token'], alert=data['alert'], extra=extra, sms=data['sms'])
                self.send_response(ACCEPTED)
            elif device == DEVICE_TYPE_IOS:
                # Use sliptlines trick to remove line ending (only for iOs).
                if type(data['alert']) is not dict:
                    alert = ''.join(data['alert'].splitlines())
                else:
                    alert = data['alert']
                data.setdefault('apns', {})
                data['apns'].setdefault('badge', data.get('badge', None))
                data['apns'].setdefault('sound', data.get('sound', None))
                data['apns'].setdefault('custom', data.get('custom', None))
                self.get_apns_conn().process(token=self.token, alert=alert, extra=extra, apns=data['apns'])
                self.send_response(ACCEPTED)
            elif device == DEVICE_TYPE_ANDROID:
                data.setdefault('gcm', {})
                try:
                    gcm = self.gcmconnections[self.app['shortname']][0]
                    response = gcm.process(token=[self.token], alert=data['alert'], extra=data['extra'], gcm=data['gcm'])
                    responsedata = response.json()
                    if responsedata['failure'] == 0:
                        self.send_response(ACCEPTED)
                except GCMUpdateRegIDsException as ex:
                    self.send_response(ACCEPTED)
                except GCMInvalidRegistrationException as ex:
                    self.send_response(BAD_REQUEST, dict(error=str(ex), regids=ex.regids))
                except GCMNotRegisteredException as ex:
                    self.send_response(BAD_REQUEST, dict(error=str(ex), regids=ex.regids))
                except GCMException as ex:
                    self.send_response(INTERNAL_SERVER_ERROR, dict(error=str(ex)))
            elif device == DEVICE_TYPE_WNS:
                data.setdefault('wns', {})
                wns = self.wnsconnections[self.app['shortname']][0]
                wns.process(token=data['token'], alert=data['alert'], extra=extra, wns=data['wns'])
                self.send_response(ACCEPTED)
            elif device == DEVICE_TYPE_MPNS:
                data.setdefault('mpns', {})
                mpns = self.mpnsconnections[self.app['shortname']][0]
                mpns.process(token=data['token'], alert=data['alert'], extra=extra, mpns=data['mpns'])
                self.send_response(ACCEPTED)
            else:
                self.send_response(BAD_REQUEST, dict(error='Invalid device type'))
            logmessage = 'Message length: %s, Access key: %s' %(len(data['alert']), self.appkey)
            self.add_to_log('%s notification' % self.appname, logmessage)
        except Exception as ex:
            import traceback
            traceback.print_exc()
            self.send_response(INTERNAL_SERVER_ERROR, dict(error=str(ex)))

